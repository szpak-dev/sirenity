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
            links = self.links(response)
            content = response.get("content", {})
            if not content:
                projected.append(ResponseDraft(
                    status=status,
                    shape="empty",
                    links=links,
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
                elif shape == "object":
                    title = definition.get("title")
                    if not isinstance(title, str) or not title:
                        raise SirenityError(
                            f"OpenAPI response schema requires a non-empty title: {status} {media_name}")
                    if any("next" in link.rel for link in links):
                        items = self.page_items(definition, links)
                        properties = definition.get("properties")
                        if not isinstance(properties, dict):
                            raise SirenityError(
                                f"OpenAPI paginated response properties must be an object: {status} {media_name}"
                            )
                        collection = self.components.schema(properties[items])
                        item_schema = collection.get("items")
                        if not isinstance(item_schema, dict):
                            raise SirenityError(
                                f"OpenAPI paginated response items require a schema: {status} {media_name}"
                            )
                        item_definition = self.components.schema(item_schema)
                        if item_definition.get("type") != "object":
                            raise SirenityError(
                                f"OpenAPI paginated response items must be objects: {status} {media_name}"
                            )
                        item_title = item_definition.get("title")
                        if not isinstance(item_title, str) or not item_title:
                            raise SirenityError(
                                f"OpenAPI paginated response items require a non-empty title: {status} {media_name}"
                            )
                        definition = definition | {
                            "properties": properties | {
                                items: collection | {"items": item_definition}
                            }
                        }
                else:
                    raise SirenityError(
                        f"OpenAPI response schema must be an object or array: {status} {media_name}"
                    )
                projected.append(ResponseDraft(
                    status=status,
                    media_type=SirenMediaType.validate(media_name),
                    shape=shape,
                    definition=definition,
                    links=links,
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
            if extension is None and name == "next":
                values = ("next",)
                link_scope = SirenScope.COLLECTION
            else:
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

    def page_items(self, definition: dict[str, Any], links: tuple[ResponseLinkDraft, ...]) -> str:
        next_links = [link for link in links if "next" in link.rel]
        if len(next_links) != 1:
            raise SirenityError("OpenAPI paginated response requires exactly one next link")
        properties = definition.get("properties")
        if not isinstance(properties, dict):
            raise SirenityError("OpenAPI paginated response requires object properties")
        candidates = []
        for name, property_schema in properties.items():
            if not isinstance(name, str) or not isinstance(property_schema, dict):
                continue
            collection = self.components.schema(property_schema)
            if collection.get("type") != "array":
                continue
            item_schema = collection.get("items")
            if isinstance(item_schema, dict) and self.components.schema(item_schema).get("type") == "object":
                candidates.append(name)
        if len(candidates) != 1:
            raise SirenityError(
                "OpenAPI paginated response requires exactly one array-of-object property"
            )
        required = definition.get("required")
        if not isinstance(required, list) or candidates[0] not in required:
            raise SirenityError("OpenAPI paginated response items property must be required")
        more = properties.get("has_more")
        if not isinstance(more, dict) or self.components.schema(more).get("type") != "boolean":
            raise SirenityError(
                "OpenAPI paginated response requires a non-nullable boolean has_more property"
            )
        required = definition.get("required")
        if not isinstance(required, list) or "has_more" not in required:
            raise SirenityError("OpenAPI paginated response has_more property must be required")
        for expression in next_links[0].parameters.values():
            self.continuation(definition, expression)
        return candidates[0]

    def continuation(self, definition: dict[str, Any], expression: str) -> None:
        prefix = "$response.body#"
        pointer = expression[len(prefix):]
        if not pointer.startswith("/"):
            raise SirenityError(
                "OpenAPI pagination continuation must reference a response property"
            )
        value = definition
        for encoded in pointer[1:].split("/"):
            token = encoded.replace("~1", "/").replace("~0", "~")
            resolved = self.components.schema(value)
            properties = resolved.get("properties")
            required = resolved.get("required")
            if (
                resolved.get("type") != "object"
                or not isinstance(properties, dict)
                or token not in properties
                or not isinstance(required, list)
                or token not in required
            ):
                raise SirenityError(
                    "OpenAPI pagination continuation properties must exist and be required"
                )
            value = properties[token]
        resolved = self.components.schema(value)
        if resolved.get("type") not in {"string", "integer", "number", "boolean"}:
            raise SirenityError(
                "OpenAPI pagination continuation properties must be non-nullable scalars"
            )

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
