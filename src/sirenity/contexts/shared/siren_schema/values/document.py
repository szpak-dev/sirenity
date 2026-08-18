from collections.abc import Mapping
from typing import Any

from sirenity.contexts.shared import BaseValue, SirenityError


class SirenSchemaDocument(BaseValue):
    """Traverse the immutable pinned official Siren schema."""

    value: Mapping[str, Any]

    def definition(self, name: str) -> Mapping[str, Any]:
        return self.definitions()[name]

    def definitions(self) -> Mapping[str, Mapping[str, Any]]:
        definitions = self.value["definitions"]
        if not isinstance(definitions, Mapping):
            raise SirenityError("Siren schema definitions must be an object.")
        return definitions

    def member(self, definition: str, name: str) -> Mapping[str, Any]:
        properties = self.effective(
            self.definition(definition)).get("properties", {})
        if not isinstance(properties, Mapping):
            raise SirenityError(
                f"Siren schema definition has invalid properties: {definition}")
        member = properties[name]
        if not isinstance(member, Mapping):
            raise SirenityError(
                f"Siren schema member must be an object: {definition}.{name}")
        return member

    def default(self, definition: str, name: str) -> str:
        default = self.member(definition, name)["default"]
        if not isinstance(default, str):
            raise SirenityError(
                f"Siren schema member must define a string default: {definition}.{name}")
        return default

    def enum(self, definition: str, name: str) -> tuple[str, ...]:
        values = self.member(definition, name)["enum"]
        if not isinstance(values, tuple) or not all(isinstance(value, str) for value in values):
            raise SirenityError(
                f"Siren schema member must define a string enum: {definition}.{name}")
        return values

    def effective(self, schema: Mapping[str, Any]) -> Mapping[str, Any]:
        if "$ref" in schema:
            reference = schema["$ref"]
            if not isinstance(reference, str):
                raise SirenityError("Siren schema reference must be a string.")
            return self.effective(self.reference(reference))
        effective = dict(schema)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for member in schema.get("allOf", ()):
            if not isinstance(member, Mapping):
                raise SirenityError(
                    "Siren schema allOf member must be an object.")
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

    def reference(self, reference: str) -> Mapping[str, Any]:
        if reference == "#":
            return self.value
        value: Any = self.value
        for segment in reference.removeprefix("#/").split("/"):
            if not isinstance(value, Mapping):
                raise SirenityError(
                    f"Siren schema reference does not resolve to an object: {reference}")
            value = value[segment]
        if not isinstance(value, Mapping):
            raise SirenityError(
                f"Siren schema reference does not resolve to an object: {reference}")
        return value

    def thaw(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return {key: self.thaw(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [self.thaw(item) for item in value]
        return value
