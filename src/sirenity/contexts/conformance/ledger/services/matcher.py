from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ....shared import SirenityError
from ... import SirenCapability, SirenRequirement
from ..contracts.matcher import SirenRequirementMatcher
from ..values.finding import SirenFinding
from ..values.report import SirenConformanceReport


@injectable(as_type=SirenRequirementMatcher)
@dataclass(frozen=True)
class SirenDefaultRequirementMatcher(SirenRequirementMatcher):
    def match(
        self, requirements: tuple[SirenRequirement, ...], capabilities: tuple[SirenCapability, ...]
    ) -> SirenConformanceReport:
        capability_by_definition = {capability.definition: capability for capability in capabilities}
        findings = tuple(
            self.finding(requirement, capability_by_definition.get(requirement.definition))
            for requirement in requirements
        )
        return SirenConformanceReport(findings=findings, features=())

    def finding(self, requirement: SirenRequirement, capability: SirenCapability | None) -> SirenFinding:
        if capability is None:
            return SirenFinding(requirement=requirement, implemented=False, evidence="no public representation")
        properties = capability.schema.get("properties", {})
        actual = properties.get(requirement.member)
        if actual is None:
            return SirenFinding(requirement=requirement, implemented=False, evidence="member is absent")
        required = capability.schema.get("required", ())
        if requirement.required and requirement.member not in required:
            return SirenFinding(requirement=requirement, implemented=False, evidence="required member is optional")
        implemented = self.matches(requirement.schema, actual, requirement.document, capability.schema)
        if requirement.supplies("enum_value"):
            implemented = implemented and requirement.enum_value in self.enum(actual, capability.schema)
        return SirenFinding(requirement=requirement, implemented=implemented, evidence="serialized public contract")

    def matches(
        self,
        expected: Mapping[str, JsonValue],
        actual: Mapping[str, JsonValue],
        expected_document: Mapping[str, JsonValue],
        actual_document: Mapping[str, JsonValue],
    ) -> bool:
        self.validate(expected)
        if "$ref" in expected:
            return self.matches(
                self.reference(expected["$ref"], expected_document), actual, expected_document, actual_document
            )
        if "$ref" in actual:
            return self.matches(
                expected,
                {
                    **self.reference(actual["$ref"], actual_document),
                    **{key: value for key, value in actual.items() if key != "$ref"},
                },
                expected_document,
                actual_document,
            )
        if "allOf" in expected:
            siblings = {key: value for key, value in expected.items() if key != "allOf"}
            return all(
                self.matches({**siblings, **value}, actual, expected_document, actual_document)
                for value in expected["allOf"]
            )
        if "anyOf" in expected or "oneOf" in expected:
            keyword = "anyOf" if "anyOf" in expected else "oneOf"
            siblings = {key: value for key, value in expected.items() if key != keyword}
            return all(
                self.matches({**siblings, **value}, actual, expected_document, actual_document)
                for value in expected[keyword]
            )
        if "allOf" in actual:
            siblings = {key: value for key, value in actual.items() if key != "allOf"}
            return all(
                self.matches(expected, {**siblings, **value}, expected_document, actual_document)
                for value in actual["allOf"]
            )
        if "anyOf" in actual or "oneOf" in actual:
            keyword = "anyOf" if "anyOf" in actual else "oneOf"
            siblings = {key: value for key, value in actual.items() if key != keyword}
            expected_types = self.types(expected)
            if expected_types:
                return all(
                    any(
                        self.matches(
                            {**expected, "type": expected_type},
                            {**siblings, **value},
                            expected_document,
                            actual_document,
                        )
                        for value in actual[keyword]
                    )
                    for expected_type in expected_types
                )
            return any(
                self.matches(expected, {**siblings, **value}, expected_document, actual_document)
                for value in actual[keyword]
            )
        expected_types = self.types(expected)
        actual_types = self.types(actual)
        types_match = not expected_types or (
            bool(actual_types)
            and all(
                value in actual_types or (value == "integer" and "number" in actual_types) for value in expected_types
            )
        )
        enum_match = "enum" not in expected or "enum" not in actual or set(expected["enum"]).issubset(actual["enum"])
        default_match = "default" not in expected or actual.get("default") == expected["default"]
        format_match = "format" not in expected or actual.get("format") == expected["format"]
        pattern_match = "pattern" not in expected or actual.get("pattern") == expected["pattern"]
        items_match = "items" not in expected or (
            "items" in actual and self.matches(expected["items"], actual["items"], expected_document, actual_document)
        )
        minimum_match = "minItems" not in expected or actual.get("minItems", 0) >= expected["minItems"]
        return all((types_match, enum_match, default_match, format_match, pattern_match, items_match, minimum_match))

    def types(self, schema: Mapping[str, JsonValue]) -> tuple[str, ...]:
        value = schema.get("type")
        match value:
            case str() as name:
                return (name,)
            case _:
                return tuple(value or ())

    def reference(self, reference: str, document: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
        if reference == "#":
            return document
        value: JsonValue = dict(document)
        for segment in reference.removeprefix("#/").split("/"):
            value = value[segment]
        return value

    def validate(self, schema: Mapping[str, JsonValue]) -> None:
        supported = {
            "$ref",
            "$schema",
            "allOf",
            "anyOf",
            "default",
            "definitions",
            "description",
            "enum",
            "format",
            "id",
            "items",
            "minItems",
            "oneOf",
            "pattern",
            "properties",
            "required",
            "title",
            "type",
        }
        unsupported = set(schema).difference(supported)
        if unsupported:
            terms = ", ".join(sorted(unsupported))
            raise SirenityError(f"Unsupported Siren schema terms: {terms}")

    def enum(
        self,
        schema: Mapping[str, JsonValue],
        document: Mapping[str, JsonValue],
    ) -> tuple[JsonValue, ...]:
        if "$ref" in schema:
            return self.enum(self.reference(schema["$ref"], document), document)
        return tuple(schema.get("enum", ()))
