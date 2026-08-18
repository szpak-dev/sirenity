from typing import Any

from sirenity.contexts.shared import (
    BaseState,
    ModwireSirenError,
    SirenActionMethod,
    SirenMediaType,
    SirenScope,
)

from ..values import ResponseDraft, ResponseLinkDraft
from .components import ComponentResolver


class OpenApiResponseProjection(BaseState):
    components: ComponentResolver

    def single_object_paths(self, paths: dict[str, Any]) -> frozenset[str]:
        selected = set()
        supported = {method.lower() for method in SirenActionMethod.values()}
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            shapes = set()
            for method, operation in path_item.items():
                if not isinstance(method, str) or method.lower() not in supported or not isinstance(operation, dict):
                    continue
                shapes.update(
                    response.shape
                    for response in self.responses(operation)
                    if response.status.startswith("2")
                )
            if "object" in shapes and "array" not in shapes:
                selected.add(path)
        return frozenset(selected)

    def responses(self, operation: dict[str, Any]) -> tuple[ResponseDraft, ...]:
        responses = operation.get("responses")
        if not isinstance(responses, dict) or not responses:
            raise ModwireSirenError("OpenAPI operation responses must be a non-empty object")
        projected: list[ResponseDraft] = []
        for status, value in responses.items():
            if not isinstance(status, str):
                raise ModwireSirenError("OpenAPI response status must be a string")
            response = self.components.response(value)
            content = response.get("content", {})
            if not content:
                projected.append(ResponseDraft(status=status, shape="empty", links=self.links(response)))
                continue
            if not isinstance(content, dict):
                raise ModwireSirenError(f"OpenAPI response content must be an object: {status}")
            for media_name, media in content.items():
                if not isinstance(media_name, str) or not isinstance(media, dict):
                    raise ModwireSirenError(f"OpenAPI response media type is invalid: {status}")
                schema = media.get("schema")
                if not isinstance(schema, dict):
                    raise ModwireSirenError(f"OpenAPI response schema is required: {status} {media_name}")
                definition = self.components.schema(schema)
                shape = definition.get("type")
                if shape == "array":
                    items = definition.get("items")
                    if not isinstance(items, dict):
                        raise ModwireSirenError(f"OpenAPI array response requires item schema: {status} {media_name}")
                    item_definition = self.components.schema(items)
                    if item_definition.get("type") != "object":
                        raise ModwireSirenError(
                            f"OpenAPI array response items must be objects: {status} {media_name}"
                        )
                    definition = definition | {"items": item_definition}
                elif shape != "object":
                    raise ModwireSirenError(
                        f"OpenAPI response schema must be an object or array: {status} {media_name}"
                    )
                projected.append(ResponseDraft(
                    status=status,
                    media_type=SirenMediaType.validate(media_name),
                    shape=shape,
                    definition=definition,
                    links=self.links(response),
                ))
        return tuple(projected)

    def links(self, response: dict[str, Any]) -> tuple[ResponseLinkDraft, ...]:
        source = response.get("links", {})
        if not isinstance(source, dict):
            raise ModwireSirenError("OpenAPI response links must be an object")
        links = []
        for name, definition in source.items():
            if not isinstance(name, str) or not isinstance(definition, dict):
                raise ModwireSirenError("OpenAPI response link is invalid")
            operation_id = definition.get("operationId")
            operation_ref = definition.get("operationRef")
            if (operation_id is None) == (operation_ref is None):
                raise ModwireSirenError(f"OpenAPI response link {name!r} requires one operation target")
            if operation_id is not None and (not isinstance(operation_id, str) or not operation_id):
                raise ModwireSirenError(f"OpenAPI response link {name!r} operationId is invalid")
            if operation_ref is not None and (not isinstance(operation_ref, str) or not operation_ref):
                raise ModwireSirenError(f"OpenAPI response link {name!r} operationRef is invalid")
            parameters = definition.get("parameters", {})
            if not isinstance(parameters, dict) or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in parameters.items()
            ):
                raise ModwireSirenError(f"OpenAPI response link {name!r} parameters are invalid")
            extension = definition.get("x-sirenity")
            if not isinstance(extension, dict):
                raise ModwireSirenError(f"OpenAPI response link {name!r} requires x-sirenity metadata")
            rel = extension.get("rel")
            scope = extension.get("scope")
            values = (rel,) if isinstance(rel, str) else tuple(rel) if isinstance(rel, list) else ()
            if not values or any(not isinstance(value, str) or not value for value in values):
                raise ModwireSirenError(f"OpenAPI response link {name!r} x-sirenity.rel is invalid")
            try:
                link_scope = SirenScope(scope)
            except (TypeError, ValueError) as error:
                raise ModwireSirenError(
                    f"OpenAPI response link {name!r} x-sirenity.scope is invalid"
                ) from error
            if link_scope == SirenScope.ROOT:
                raise ModwireSirenError(f"OpenAPI response link {name!r} cannot target root scope")
            links.append(ResponseLinkDraft(
                operation_id=operation_id,
                operation_ref=operation_ref,
                parameters=parameters,
                rel=values,
                scope=link_scope,
            ))
        return tuple(links)
