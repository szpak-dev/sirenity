from copy import deepcopy
from typing import Any

from pydantic import Field

from sirenity.contexts.shared import BaseState, SirenityError


class ComponentResolver(BaseState):
    components: Any
    reference_cache: dict[tuple[str, str],
                          dict[str, Any]] = Field(default_factory=dict)

    def parameter(self, definition: Any) -> dict[str, Any]:
        return self.resolve(definition, "parameters")

    def request_body(self, definition: Any) -> dict[str, Any]:
        return self.resolve(definition, "requestBodies")

    def response(self, definition: Any) -> dict[str, Any]:
        return self.resolve(definition, "responses")

    def schema(self, definition: Any) -> dict[str, Any]:
        return self.resolve(definition, "schemas")

    def schema_tree(self, definition: Any, trail: tuple[str, ...] = ()) -> Any:
        if isinstance(definition, list):
            return [self.schema_tree(value, trail) for value in definition]
        if not isinstance(definition, dict):
            return deepcopy(definition)
        reference = definition.get("$ref")
        if reference is not None and not isinstance(reference, str):
            raise SirenityError("OpenAPI component reference must be a string")
        if isinstance(reference, str) and reference in trail:
            return deepcopy(definition)
        resolved = self.schema(
            definition) if reference is not None else deepcopy(definition)
        nested_trail = (
            *trail, reference) if isinstance(reference, str) else trail
        return {name: self.schema_tree(value, nested_trail) for name, value in resolved.items()}

    def resolve(self, definition: Any, kind: str, trail: tuple[str, ...] = ()) -> dict[str, Any]:
        if not isinstance(definition, dict):
            return {}
        result = deepcopy(definition)
        reference = result.pop("$ref", None)
        if reference is None:
            return result
        if not isinstance(reference, str):
            raise SirenityError("OpenAPI component reference must be a string")
        if reference in trail:
            raise SirenityError(
                f"OpenAPI component reference cycle: {' -> '.join((*trail, reference))}")
        component_kind, name = self.address(reference, kind)
        cache_key = component_kind, name
        cached = self.reference_cache.get(cache_key)
        if cached is not None:
            return deepcopy(cached) | result
        collection = self.components.get(component_kind) if isinstance(
            self.components, dict) else None
        target = collection.get(name) if isinstance(collection, dict) else None
        if not isinstance(target, dict):
            raise SirenityError(
                f"OpenAPI component reference is unknown: {reference}")
        resolved = self.resolve(target, kind, (*trail, reference))
        self.reference_cache[cache_key] = resolved
        return deepcopy(resolved) | result

    def address(self, reference: str, expected_kind: str) -> tuple[str, str]:
        prefix = "#/components/"
        if not reference.startswith(prefix):
            raise SirenityError(
                f"OpenAPI component reference is unsupported: {reference}")
        parts = reference[len(prefix):].split("/")
        if len(parts) != 2:
            raise SirenityError(
                f"OpenAPI component reference is invalid: {reference}")
        kind, encoded_name = parts
        if kind != expected_kind:
            raise SirenityError(
                f"OpenAPI component reference {reference!r} must target components/{expected_kind}, "
                f"not components/{kind}"
            )
        return kind, self.decode(encoded_name, reference)

    def decode(self, token: str, reference: str) -> str:
        decoded = ""
        index = 0
        while index < len(token):
            character = token[index]
            if character != "~":
                decoded += character
                index += 1
                continue
            if index + 1 == len(token) or token[index + 1] not in {"0", "1"}:
                raise SirenityError(
                    f"OpenAPI component reference is invalid: {reference}")
            decoded += "~" if token[index + 1] == "0" else "/"
            index += 2
        return decoded
