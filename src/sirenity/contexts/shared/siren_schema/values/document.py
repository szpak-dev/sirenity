from collections.abc import Mapping

from pydantic import JsonValue

from ... import BaseValue


class SirenSchemaDocument(BaseValue):
    """Traverse the immutable pinned official Siren schema."""

    value: Mapping[str, JsonValue]

    def definition(self, name: str) -> Mapping[str, JsonValue]:
        return self.definitions()[name]

    def definitions(self) -> Mapping[str, Mapping[str, JsonValue]]:
        return self.value["definitions"]

    def member(self, definition: str, name: str) -> Mapping[str, JsonValue]:
        properties = self.effective(self.definition(definition)).get("properties", {})
        return properties[name]

    def default(self, definition: str, name: str) -> str:
        return self.member(definition, name)["default"]

    def enum(self, definition: str, name: str) -> tuple[str, ...]:
        return self.member(definition, name)["enum"]

    def effective(self, schema: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
        if "$ref" in schema:
            return self.effective(self.reference(schema["$ref"]))
        effective = dict(schema)
        properties: dict[str, JsonValue] = {}
        required: list[str] = []
        for member in schema.get("allOf", ()):
            incoming = self.effective(member)
            properties.update(incoming.get("properties", {}))
            required.extend(incoming.get("required", ()))
        properties.update(schema.get("properties", {}))
        required.extend(schema.get("required", ()))
        if properties:
            effective["properties"] = properties
        if required:
            effective["required"] = tuple(dict.fromkeys(required))
        return effective

    def reference(self, reference: str) -> Mapping[str, JsonValue]:
        if reference == "#":
            return self.value
        value: JsonValue = dict(self.value)
        for segment in reference.removeprefix("#/").split("/"):
            value = value[segment]
        return value

    def thaw(self, value: JsonValue) -> JsonValue:
        return value
