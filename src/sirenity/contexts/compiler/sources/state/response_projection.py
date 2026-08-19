from typing import Any

from sirenity.contexts.shared import (
    BaseState,
    SirenActionMethod,
    SirenityError,
    SirenMediaType,
    SirenScope,
)

from ..values import ResponseDraft, ResponseLinkDraft, RuntimeBindingDraft
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
            raise SirenityError(
                "OpenAPI operation responses must be a non-empty object")
        projected: list[ResponseDraft] = []
        for status, value in responses.items():
            if not isinstance(status, str):
                raise SirenityError("OpenAPI response status must be a string")
            response = self.components.response(value)
            content = response.get("content", {})
            if not content:
                projected.append(ResponseDraft(
                    status=status,
                    shape="empty",
                    links=self.links(response),
                    bindings=self.bindings(response),
                ))
                continue
            if not isinstance(content, dict):
                raise SirenityError(
                    f"OpenAPI response content must be an object: {status}")
            for media_name, media in content.items():
                if not isinstance(media_name, str) or not isinstance(media, dict):
                    raise SirenityError(
                        f"OpenAPI response media type is invalid: {status}")
                schema = media.get("schema")
                if not isinstance(schema, dict):
                    raise SirenityError(
                        f"OpenAPI response schema is required: {status} {media_name}")
                definition = self.components.schema(schema)
                shape = definition.get("type")
                if shape == "array":
                    items = definition.get("items")
                    if not isinstance(items, dict):
                        raise SirenityError(
                            f"OpenAPI array response requires item schema: {status} {media_name}")
                    item_definition = self.components.schema(items)
                    if item_definition.get("type") != "object":
                        raise SirenityError(
                            f"OpenAPI array response items must be objects: {status} {media_name}"
                        )
                    item_title = item_definition.get("title")
                    if not isinstance(item_title, str) or not item_title:
                        raise SirenityError(
                            f"OpenAPI array response items require a non-empty title: {status} {media_name}")
                    definition = definition | {"items": item_definition}
                elif shape != "object":
                    raise SirenityError(
                        f"OpenAPI response schema must be an object or array: {status} {media_name}"
                    )
                title = definition.get("title")
                if not isinstance(title, str) or not title:
                    raise SirenityError(
                        f"OpenAPI response schema requires a non-empty title: {status} {media_name}")
                projected.append(ResponseDraft(
                    status=status,
                    media_type=SirenMediaType.validate(media_name),
                    shape=shape,
                    definition=definition,
                    links=self.links(response),
                    bindings=self.bindings(response),
                ))
        return tuple(projected)

    def links(self, response: dict[str, Any]) -> tuple[ResponseLinkDraft, ...]:
        source = response.get("links", {})
        if not isinstance(source, dict):
            raise SirenityError("OpenAPI response links must be an object")
        links = []
        for name, definition in source.items():
            if not isinstance(name, str) or not isinstance(definition, dict):
                raise SirenityError("OpenAPI response link is invalid")
            operation_id = definition.get("operationId")
            operation_ref = definition.get("operationRef")
            if (operation_id is None) == (operation_ref is None):
                raise SirenityError(
                    f"OpenAPI response link {name!r} requires one operation target")
            if operation_id is not None and (not isinstance(operation_id, str) or not operation_id):
                raise SirenityError(
                    f"OpenAPI response link {name!r} operationId is invalid")
            if operation_ref is not None and (not isinstance(operation_ref, str) or not operation_ref):
                raise SirenityError(
                    f"OpenAPI response link {name!r} operationRef is invalid")
            parameters = definition.get("parameters", {})
            if not isinstance(parameters, dict) or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in parameters.items()
            ):
                raise SirenityError(
                    f"OpenAPI response link {name!r} parameters are invalid")
            extension = definition.get("x-sirenity")
            if not isinstance(extension, dict):
                raise SirenityError(
                    f"OpenAPI response link {name!r} requires x-sirenity metadata")
            rel = extension.get("rel")
            scope = extension.get("scope")
            values = (rel,) if isinstance(rel, str) else tuple(
                rel) if isinstance(rel, list) else ()
            if not values or any(not isinstance(value, str) or not value for value in values):
                raise SirenityError(
                    f"OpenAPI response link {name!r} x-sirenity.rel is invalid")
            try:
                link_scope = SirenScope(scope)
            except (TypeError, ValueError) as error:
                raise SirenityError(
                    f"OpenAPI response link {name!r} x-sirenity.scope is invalid"
                ) from error
            if link_scope == SirenScope.ROOT:
                raise SirenityError(
                    f"OpenAPI response link {name!r} cannot target root scope")
            links.append(ResponseLinkDraft(
                operation_id=operation_id,
                operation_ref=operation_ref,
                parameters=parameters,
                rel=values,
                scope=link_scope,
            ))
        return tuple(links)

    def bindings(self, response: dict[str, Any]) -> tuple[RuntimeBindingDraft, ...]:
        extension = response.get("x-sirenity", {})
        if not isinstance(extension, dict):
            raise SirenityError("OpenAPI response x-sirenity metadata must be an object")
        source = extension.get("actionBindings", {})
        if not isinstance(source, dict):
            raise SirenityError("OpenAPI response action bindings must be an object")
        bindings = []
        for operation, fields in source.items():
            if not isinstance(operation, str) or not operation or not isinstance(fields, dict):
                raise SirenityError("OpenAPI response action binding is invalid")
            if not fields or any(
                not isinstance(name, str) or not name or not isinstance(expression, str)
                for name, expression in fields.items()
            ):
                raise SirenityError("OpenAPI response action binding fields are invalid")
            bindings.append(RuntimeBindingDraft(operation=operation, fields=fields))
        return tuple(bindings)
