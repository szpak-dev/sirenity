from dataclasses import dataclass
from typing import Literal

from pydantic import JsonValue
from wireup import injectable

from ....graph import SirenField
from ....shared import SirenFieldType, SirenityError
from ..values.compilation_request import OpenApiCompilationRequest
from .components import ComponentResolver


@injectable
@dataclass(frozen=True)
class OpenApiFieldProjection:
    components: ComponentResolver

    def delegated_kind(
        self, request: OpenApiCompilationRequest, name: str, schema: dict[str, JsonValue]
    ) -> Literal["array", "object", "json"] | None:
        definition = self.components.schema(request, schema)
        for keyword in ("anyOf", "oneOf"):
            variants = definition.get(keyword)
            if variants:
                kinds = tuple(self.delegated_kind(request, name, variant) for variant in variants)
                if any(kind is None for kind in kinds):
                    return None
                return kinds[0] if len(set(kinds)) == 1 else "json"
        schema_type = definition.get("type")
        if schema_type == "object":
            properties = definition.get("properties")
            additional = definition.get("additionalProperties", True)
            if not properties and (additional is True or additional == {}):
                return "json"
            return "object"
        if schema_type == "array":
            return None if self.values(request, name, definition) else "array"
        return None

    def field(self, request: OpenApiCompilationRequest, name: str, schema: dict[str, JsonValue]) -> SirenField:
        definition = self.definition(request, name, schema)
        values = self.values(request, name, definition)
        field_type = self.type(request, name, definition, values)
        title = definition.get("title")
        default = definition.get("default")
        if not title:
            raise SirenityError(f"OpenAPI field schema requires a non-empty title: {name}")
        if values and default is not None and default not in values:
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        return SirenField(name=name, type=field_type, values=values, title=title, default=default)

    def definition(
        self, request: OpenApiCompilationRequest, name: str, schema: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        definition = self.components.schema(request, schema)
        definition = self.all_of(request, name, definition)
        definition = self.scalar_composition(request, name, definition, "oneOf")
        definition = self.scalar_composition(request, name, definition, "anyOf")
        schema_type = definition.get("type")
        match schema_type:
            case [*values]:
                values = [value for value in values if value != "null"]
                if len(values) != 1:
                    raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
                definition = {**definition, "type": values[0], "nullable": True}
        return definition

    def all_of(
        self, request: OpenApiCompilationRequest, name: str, definition: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        variants = definition.get("allOf")
        if variants is None:
            return definition
        if not variants:
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        merged = {key: value for key, value in definition.items() if key != "allOf"}
        for variant in variants:
            for key, value in self.definition(request, name, variant).items():
                existing = merged.get(key)
                if key in merged and existing != value:
                    raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
                merged[key] = value
        return merged

    def scalar_composition(
        self,
        request: OpenApiCompilationRequest,
        name: str,
        definition: dict[str, JsonValue],
        keyword: str,
    ) -> dict[str, JsonValue]:
        variants = definition.get(keyword)
        if variants is None:
            return definition
        scalar = [variant for variant in variants if variant.get("type") != "null"]
        nulls = [variant for variant in variants if variant.get("type") == "null"]
        if len(scalar) != 1 or len(nulls) + len(scalar) != len(variants):
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        normalized = self.definition(request, name, scalar[0])
        outer = {key: value for key, value in definition.items() if key != keyword}
        for key, value in outer.items():
            if key in normalized and normalized[key] != value:
                raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        return {**normalized, **outer, "nullable": bool(nulls) or normalized.get("nullable") is True}

    def values(
        self, request: OpenApiCompilationRequest, name: str, definition: dict[str, JsonValue]
    ) -> tuple[str | int | float, ...]:
        source = definition.get("enum")
        if source is None and definition.get("type") == "array":
            items = definition["items"]
            source = self.definition(request, name, items).get("enum")
        if source is None:
            return ()
        values = tuple(value for value in source if value is not None)
        if not values:
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        return values

    def type(
        self,
        request: OpenApiCompilationRequest,
        name: str,
        definition: dict[str, JsonValue],
        values: tuple[str | int | float, ...],
    ) -> SirenFieldType:
        unsupported = {"const", "contains", "if", "not", "prefixItems"}
        if unsupported & definition.keys():
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        schema_type = definition.get("type")
        if schema_type == "array":
            items = definition["items"]
            item_definition = self.definition(request, name, items)
            if item_definition.get("type") == "array":
                raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
            self.type(request, name, item_definition, ())
            if values:
                return SirenFieldType.validate("checkbox")
            raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
        if values:
            return SirenFieldType.validate("radio")
        if schema_type == "string":
            formats = {
                None: SirenFieldType.default(),
                "date": SirenFieldType.validate("date"),
                "date-time": SirenFieldType.validate("datetime-local"),
                "email": SirenFieldType.validate("email"),
                "time": SirenFieldType.validate("time"),
                "uri": SirenFieldType.validate("url"),
                "uuid": SirenFieldType.default(),
            }
            field_type = formats.get(definition.get("format"))
            if field_type is not None:
                return field_type
        if schema_type in {"integer", "number"}:
            return SirenFieldType.validate("number")
        if schema_type == "boolean":
            return SirenFieldType.validate("checkbox")
        raise SirenityError(f"OpenAPI field schema is unsupported: {name}")
