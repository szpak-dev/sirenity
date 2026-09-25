import re
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ....graph.model import SirenContinuationKind
from ....shared import SirenActionMethod, SirenityError, SirenMediaType, SirenScope
from ..values.compilation_request import OpenApiCompilationRequest
from ..values.response_binding import ResponseBindingDraft
from ..values.response_continuation import (
    ResponseContinuationDraft,
    ResponseContinuationParameter,
    ResponseOperationTarget,
)
from ..values.response_draft import ResponseDraft
from ..values.response_item_link_draft import ResponseItemLinkDraft
from ..values.response_link_draft import ResponseLinkDraft
from ..values.response_source_input import ResponseSourceInputDraft
from .components import ComponentResolver


@injectable
@dataclass(frozen=True)
class OpenApiResponseProjection:
    components: ComponentResolver

    def single_object_paths(self, request: OpenApiCompilationRequest) -> frozenset[str]:
        selected = set()
        supported = {method.lower() for method in SirenActionMethod.values()}
        for path, path_item in request.paths.items():
            shapes = set()
            for method, operation in path_item.items():
                if method.lower() not in supported:
                    continue
                shapes.update(
                    response.shape for response in self.responses(request, operation) if response.status.startswith("2")
                )
            if "object" in shapes and "array" not in shapes:
                selected.add(path)
        return frozenset(selected)

    def responses(
        self, request: OpenApiCompilationRequest, operation: dict[str, JsonValue]
    ) -> tuple[ResponseDraft, ...]:
        responses = operation["responses"]
        if not responses:
            raise SirenityError("OpenAPI operation responses must be a non-empty object")
        projected: list[ResponseDraft] = []
        for status, value in responses.items():
            response = self.components.response(request, value)
            links = self.links(response)
            item_links = self.item_links(response)
            continuations = self.continuations(response)
            content = response.get("content", {})
            if not content:
                if continuations:
                    raise SirenityError("OpenAPI continuation response requires object content")
                if item_links:
                    raise SirenityError("OpenAPI item follow-up response requires object content")
                projected.append(
                    ResponseDraft(
                        status=status,
                        shape="empty",
                        links=links,
                        item_links=item_links,
                        continuations=continuations,
                        bindings=self.bindings(response),
                    )
                )
                continue
            for media_name, media in content.items():
                schema = media["schema"]
                definition = self.components.schema(request, schema)
                shape = definition.get("type")
                if shape == "array":
                    if continuations:
                        raise SirenityError("OpenAPI continuation response requires object content")
                    if item_links:
                        raise SirenityError("OpenAPI item follow-up response requires object content")
                    items = definition["items"]
                    item_definition = self.components.schema(request, items)
                    if item_definition.get("type") != "object":
                        raise SirenityError(f"OpenAPI array response items must be objects: {status} {media_name}")
                    item_title = item_definition.get("title")
                    if not item_title:
                        raise SirenityError(
                            f"OpenAPI array response items require a non-empty title: {status} {media_name}"
                        )
                    definition = definition | {"items": item_definition}
                elif shape == "object":
                    title = definition.get("title")
                    if not title:
                        raise SirenityError(
                            f"OpenAPI response schema requires a non-empty title: {status} {media_name}"
                        )
                    self.validate_continuations(request, definition, continuations)
                    self.validate_item_links(request, definition, item_links)
                    pagination = any(
                        continuation.kind == SirenContinuationKind.PAGINATION for continuation in continuations
                    )
                    if item_links and not pagination:
                        raise SirenityError("OpenAPI item follow-ups require a paginated response")
                    if pagination:
                        items = self.page_items(request, definition)
                        if any(
                            self.item_property(link.item_collection, "collection") != items
                            for link in item_links
                        ):
                            raise SirenityError("OpenAPI item follow-up must select the paginated item collection")
                        properties = definition["properties"]
                        collection = self.components.schema(request, properties[items])
                        item_schema = collection["items"]
                        item_definition = self.components.schema(request, item_schema)
                        if item_definition.get("type") != "object":
                            raise SirenityError(
                                f"OpenAPI paginated response items must be objects: {status} {media_name}"
                            )
                        item_title = item_definition.get("title")
                        if not item_title:
                            raise SirenityError(
                                f"OpenAPI paginated response items require a non-empty title: {status} {media_name}"
                            )
                        definition = definition | {
                            "properties": properties | {items: collection | {"items": item_definition}}
                        }
                else:
                    raise SirenityError(f"OpenAPI response schema must be an object or array: {status} {media_name}")
                projected.append(
                    ResponseDraft(
                        status=status,
                        media_type=SirenMediaType.validate(media_name),
                        shape=shape,
                        definition=definition,
                        links=links,
                        item_links=item_links,
                        continuations=continuations,
                        bindings=self.bindings(response),
                    )
                )
        return tuple(projected)

    def links(self, response: dict[str, JsonValue]) -> tuple[ResponseLinkDraft, ...]:
        source = response.get("links", {})
        links = []
        for name, definition in source.items():
            if self.is_continuation(name, definition) or self.is_item_link(definition):
                continue
            operation_id = definition.get("operationId")
            operation_ref = definition.get("operationRef")
            if (operation_id is None) == (operation_ref is None):
                raise SirenityError(f"OpenAPI response link {name!r} requires one operation target")
            if operation_id is not None and not operation_id:
                raise SirenityError(f"OpenAPI response link {name!r} operationId is invalid")
            if operation_ref is not None and not operation_ref:
                raise SirenityError(f"OpenAPI response link {name!r} operationRef is invalid")
            parameters = definition.get("parameters", {})
            extension = definition.get("x-sirenity")
            if extension is None and name == "next":
                values = ("next",)
                link_scope = SirenScope.COLLECTION
            else:
                values = (extension["rel"],)
                if not values[0]:
                    raise SirenityError(f"OpenAPI response link {name!r} x-sirenity.rel is invalid")
                link_scope = SirenScope(extension["scope"])
                if link_scope == SirenScope.ROOT:
                    raise SirenityError(f"OpenAPI response link {name!r} cannot target root scope")
            links.append(
                ResponseLinkDraft(
                    parameters=parameters,
                    rel=values,
                    scope=link_scope,
                    source_inputs=self.source_inputs(definition),
                    **({"operation_id": operation_id} if operation_id is not None else {}),
                    **({"operation_ref": operation_ref} if operation_ref is not None else {}),
                )
            )
        return tuple(links)

    def item_links(self, response: dict[str, JsonValue]) -> tuple[ResponseItemLinkDraft, ...]:
        links = []
        for name, definition in response.get("links", {}).items():
            if not self.is_item_link(definition):
                continue
            operation_id = definition.get("operationId")
            operation_ref = definition.get("operationRef")
            if (operation_id is None) == (operation_ref is None):
                raise SirenityError(f"OpenAPI response link {name!r} requires one operation target")
            if operation_id is not None and not operation_id:
                raise SirenityError(f"OpenAPI response link {name!r} operationId is invalid")
            if operation_ref is not None and not operation_ref:
                raise SirenityError(f"OpenAPI response link {name!r} operationRef is invalid")
            extension = definition["x-sirenity"]
            relation = extension["rel"]
            if not relation:
                raise SirenityError(f"OpenAPI response link {name!r} x-sirenity.rel is invalid")
            scope = SirenScope(extension["scope"])
            if scope == SirenScope.ROOT:
                raise SirenityError(f"OpenAPI response link {name!r} cannot target root scope")
            links.append(
                ResponseItemLinkDraft(
                    parameters=definition.get("parameters", {}),
                    rel=(relation,),
                    scope=scope,
                    source_inputs=self.source_inputs(definition),
                    item_collection=extension["itemCollection"],
                    **({"operation_id": operation_id} if operation_id is not None else {}),
                    **({"operation_ref": operation_ref} if operation_ref is not None else {}),
                )
            )
        return tuple(links)

    def is_item_link(self, definition: dict[str, JsonValue]) -> bool:
        extension = definition.get("x-sirenity")
        return extension is not None and "itemCollection" in extension

    def continuations(self, response: dict[str, JsonValue]) -> tuple[ResponseContinuationDraft, ...]:
        source = response.get("links", {})
        continuations = tuple(
            ResponseContinuationDraft(
                target=self.operation_target(name, definition),
                kind=self.continuation_kind(name, definition),
                parameters=self.continuation_parameters(name, definition),
                source_inputs=self.source_inputs(definition),
            )
            for name, definition in source.items()
            if self.is_continuation(name, definition)
        )
        if len(continuations) > 1:
            raise SirenityError("OpenAPI response requires at most one continuation")
        return continuations

    def is_continuation(self, name: str, definition: dict[str, JsonValue]) -> bool:
        if name == "next":
            return True
        extension = definition.get("x-sirenity")
        if extension is None:
            return False
        return extension.get("rel") == "next" or "continuation" in extension

    def operation_target(self, name: str, definition: dict[str, JsonValue]) -> ResponseOperationTarget:
        operation_id = definition.get("operationId")
        operation_ref = definition.get("operationRef")
        if (operation_id is None) == (operation_ref is None):
            raise SirenityError(f"OpenAPI response link {name!r} requires one operation target")
        if operation_id is not None:
            if not operation_id:
                raise SirenityError(f"OpenAPI response link {name!r} operationId is invalid")
            return ResponseOperationTarget(kind="operation_id", value=operation_id)
        if not operation_ref:
            raise SirenityError(f"OpenAPI response link {name!r} operationRef is invalid")
        return ResponseOperationTarget(kind="operation_ref", value=operation_ref)

    def continuation_kind(self, name: str, definition: dict[str, JsonValue]) -> SirenContinuationKind:
        extension = definition.get("x-sirenity")
        if extension is None:
            if name != "next":
                raise SirenityError(f"OpenAPI response link {name!r} requires x-sirenity metadata")
            return SirenContinuationKind.PAGINATION
        declared = extension.get("continuation", SirenContinuationKind.PAGINATION)
        return SirenContinuationKind(declared)

    def continuation_parameters(
        self, name: str, definition: dict[str, JsonValue]
    ) -> tuple[ResponseContinuationParameter, ...]:
        parameters = definition.get("parameters", {})
        if any(not parameter or not expression for parameter, expression in parameters.items()):
            raise SirenityError(f"OpenAPI response link {name!r} parameters are invalid")
        return tuple(
            ResponseContinuationParameter(name=parameter, expression=expression)
            for parameter, expression in parameters.items()
        )

    def source_inputs(self, definition: dict[str, JsonValue]) -> tuple[ResponseSourceInputDraft, ...]:
        extension = definition.get("x-sirenity", {})
        return tuple(
            ResponseSourceInputDraft(target=target, expression=expression)
            for target, expression in extension.get("sourceInputs", {}).items()
        )

    def validate_continuations(
        self,
        request: OpenApiCompilationRequest,
        definition: dict[str, JsonValue],
        continuations: tuple[ResponseContinuationDraft, ...],
    ) -> None:
        if not continuations:
            return
        properties = definition["properties"]
        required = definition["required"]
        resolved = self.components.schema(request, properties["has_more"])
        pagination = continuations[0].kind == SirenContinuationKind.PAGINATION
        if resolved.get("type") != "boolean" or resolved.get("nullable") is True:
            raise SirenityError(
                "OpenAPI paginated response requires a non-nullable boolean has_more property"
                if pagination
                else "OpenAPI bounded continuation requires a non-nullable boolean has_more property"
            )
        if "has_more" not in required:
            raise SirenityError(
                "OpenAPI paginated response has_more property must be required"
                if pagination
                else "OpenAPI bounded continuation has_more property must be required"
            )
        for parameter in continuations[0].parameters:
            self.continuation(request, definition, parameter.expression)

    def validate_item_links(
        self,
        request: OpenApiCompilationRequest,
        definition: dict[str, JsonValue],
        item_links: tuple[ResponseItemLinkDraft, ...],
    ) -> None:
        if not item_links:
            return
        properties = definition.get("properties", {})
        required = definition.get("required", ())
        for link in item_links:
            collection_name = self.item_property(link.item_collection, "collection")
            if collection_name not in properties or collection_name not in required:
                raise SirenityError("OpenAPI item follow-up collection must exist and be required")
            collection = self.components.schema(request, properties[collection_name])
            if collection.get("type") != "array" or collection.get("nullable") is True:
                raise SirenityError("OpenAPI item follow-up collection must be a non-nullable array")
            item = self.components.schema(request, collection["items"])
            if item.get("type") != "object":
                raise SirenityError("OpenAPI item follow-up collection items must be objects")
            item_properties = item.get("properties", {})
            item_required = item.get("required", ())
            for expression in link.parameters.values():
                property_name = self.item_property(expression, "parameter")
                if property_name not in item_properties or property_name not in item_required:
                    raise SirenityError("OpenAPI item follow-up properties must exist and be required")
                value = self.components.schema(request, item_properties[property_name])
                if value.get("type") not in {"string", "integer", "number", "boolean"} or value.get(
                    "nullable"
                ) is True:
                    raise SirenityError("OpenAPI item follow-up properties must be non-nullable scalars")

    def item_property(self, expression: str, source: str) -> str:
        prefix = "$response.body#/"
        if not expression.startswith(prefix):
            raise SirenityError(f"OpenAPI item follow-up {source} expression is unsupported")
        encoded = expression[len(prefix) :]
        if not encoded or "/" in encoded or re.search(r"~(?:[^01]|$)", encoded):
            raise SirenityError(f"OpenAPI item follow-up {source} expression is invalid")
        return encoded.replace("~1", "/").replace("~0", "~")

    def page_items(self, request: OpenApiCompilationRequest, definition: dict[str, JsonValue]) -> str:
        properties = definition["properties"]
        candidates = []
        for name, property_schema in properties.items():
            collection = self.components.schema(request, property_schema)
            if collection.get("type") != "array":
                continue
            item_schema = collection.get("items", {})
            if self.components.schema(request, item_schema).get("type") == "object":
                candidates.append(name)
        if len(candidates) != 1:
            raise SirenityError("OpenAPI paginated response requires exactly one array-of-object property")
        required = definition.get("required")
        if candidates[0] not in required:
            raise SirenityError("OpenAPI paginated response items property must be required")
        return candidates[0]

    def continuation(
        self,
        request: OpenApiCompilationRequest,
        definition: dict[str, JsonValue],
        expression: str,
    ) -> None:
        prefix = "$response.body#"
        if not expression.startswith(prefix):
            raise SirenityError("OpenAPI continuation runtime expression is unsupported")
        pointer = expression[len(prefix) :]
        if not pointer.startswith("/"):
            raise SirenityError("OpenAPI continuation must reference a response property")
        value = definition
        for encoded in pointer[1:].split("/"):
            if not encoded or re.search(r"~(?:[^01]|$)", encoded):
                raise SirenityError("OpenAPI continuation response pointer is invalid")
            token = encoded.replace("~1", "/").replace("~0", "~")
            resolved = self.components.schema(request, value)
            properties = resolved.get("properties")
            required = resolved.get("required")
            if resolved.get("type") != "object" or token not in properties or token not in required:
                raise SirenityError("OpenAPI continuation properties must exist and be required")
            value = properties[token]
        resolved = self.components.schema(request, value)
        if resolved.get("type") not in {"string", "integer", "number", "boolean"} or resolved.get("nullable") is True:
            raise SirenityError("OpenAPI continuation properties must be non-nullable scalars")

    def bindings(self, response: dict[str, JsonValue]) -> tuple[ResponseBindingDraft, ...]:
        extension = response.get("x-sirenity", {})
        source = extension.get("actionBindings", {})
        bindings = []
        for operation, fields in source.items():
            if not operation:
                raise SirenityError("OpenAPI response action binding is invalid")
            if not fields or any(not name or not expression for name, expression in fields.items()):
                raise SirenityError("OpenAPI response action binding fields are invalid")
            bindings.append(ResponseBindingDraft(operation=operation, fields=fields))
        return tuple(bindings)
