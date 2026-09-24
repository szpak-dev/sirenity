from copy import deepcopy
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ....shared import SirenityError
from ..values.compilation_request import OpenApiCompilationRequest


@injectable
@dataclass(frozen=True)
class ComponentResolver:
    def parameter(self, request: OpenApiCompilationRequest, definition: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return self.resolve(request, definition, "parameters", ())

    def request_body(
        self, request: OpenApiCompilationRequest, definition: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        return self.resolve(request, definition, "requestBodies", ())

    def response(self, request: OpenApiCompilationRequest, definition: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return self.resolve(request, definition, "responses", ())

    def schema(self, request: OpenApiCompilationRequest, definition: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return self.resolve(request, definition, "schemas", ())

    def schema_tree(
        self, request: OpenApiCompilationRequest, definition: JsonValue, trail: tuple[str, ...]
    ) -> JsonValue:
        match definition:
            case list() as values:
                return [self.schema_tree(request, value, trail) for value in values]
            case dict() as value:
                definition = value
            case _:
                return deepcopy(definition)
        reference = definition.get("$ref")
        if reference in trail:
            return deepcopy(definition)
        resolved = self.schema(request, definition) if reference is not None else deepcopy(definition)
        nested_trail = (*trail, reference) if reference is not None else trail
        return {name: self.schema_tree(request, value, nested_trail) for name, value in resolved.items()}

    def resolve(
        self,
        request: OpenApiCompilationRequest,
        definition: dict[str, JsonValue],
        kind: str,
        trail: tuple[str, ...],
    ) -> dict[str, JsonValue]:
        result = deepcopy(definition)
        reference = result.pop("$ref", None)
        if reference is None:
            return result
        if reference in trail:
            raise SirenityError(f"OpenAPI component reference cycle: {' -> '.join((*trail, reference))}")
        component_kind, name = self.address(reference, kind)
        components = request.document.get("components", {})
        collection = components.get(component_kind, {})
        target = collection.get(name)
        if target is None:
            raise SirenityError(f"OpenAPI component reference is unknown: {reference}")
        resolved = self.resolve(request, target, kind, (*trail, reference))
        return deepcopy(resolved) | result

    def address(self, reference: str, expected_kind: str) -> tuple[str, str]:
        prefix = "#/components/"
        if not reference.startswith(prefix):
            raise SirenityError(f"OpenAPI component reference is unsupported: {reference}")
        parts = reference[len(prefix) :].split("/")
        if len(parts) != 2:
            raise SirenityError(f"OpenAPI component reference is invalid: {reference}")
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
                raise SirenityError(f"OpenAPI component reference is invalid: {reference}")
            decoded += "~" if token[index + 1] == "0" else "/"
            index += 2
        return decoded
