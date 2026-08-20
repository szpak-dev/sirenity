from typing import Any, ClassVar

from sirenity.contexts.shared import (
    BaseState,
    SirenActionMethod,
    SirenHttpMethod,
    SirenityError,
    SirenMediaType,
    SirenScope,
)

from ..values import DelegatedInputDraft, Field, InputDraft, ParameterInputDraft
from .assembly import SirenAssembly
from .components import ComponentResolver
from .field_projection import OpenApiFieldProjection
from .response_projection import OpenApiResponseProjection
from .routes import RouteCatalog


class OpenApiOperationCompiler(BaseState):
    methods: ClassVar[frozenset[SirenHttpMethod]] = frozenset(
        SirenHttpMethod(value) for value in SirenActionMethod.values()
    )
    assembly: SirenAssembly
    routes: RouteCatalog
    components: ComponentResolver
    projection: OpenApiFieldProjection
    responses: OpenApiResponseProjection

    def compile(self) -> None:
        for path, path_item in self.routes.paths.items():
            if not isinstance(path_item, dict):
                continue
            if "$ref" in path_item:
                raise SirenityError(
                    f"OpenAPI path item reference is unsupported: {path}")
            for method, operation in path_item.items():
                method_name = method.lower()
                if method_name == "trace":
                    raise SirenityError(
                        f"OpenAPI operation method is unsupported: {method.upper()} {path}")
                try:
                    operation_method = SirenHttpMethod(method.upper())
                except ValueError:
                    continue
                if operation_method in {SirenHttpMethod.HEAD, SirenHttpMethod.OPTIONS}:
                    raise SirenityError(
                        f"OpenAPI operation method is unsupported: {method.upper()} {path}")
                if operation_method not in self.methods or not isinstance(operation, dict):
                    continue
                name = operation.get("operationId")
                if not isinstance(name, str) or not name:
                    raise SirenityError(
                        f"OpenAPI operation requires operationId: {method.upper()} {path}")
                title = operation.get("summary")
                if not isinstance(title, str) or not title:
                    raise SirenityError(
                        f"OpenAPI operation requires a non-empty summary: {method.upper()} {path}")
                description = operation.get("description")
                if not isinstance(description, str) or not description:
                    raise SirenityError(
                        f"OpenAPI operation requires a non-empty description: {method.upper()} {path}")
                ownership = self.routes.ownership(path)
                fields, input = self.input(path_item, operation)
                media_type = input.media_type if input else None
                responses = self.response_links(
                    self.responses.responses(operation))
                if ownership is None:
                    self.assembly.add_operation(
                        None,
                        SirenScope.ROOT,
                        name,
                        operation_method,
                        self.routes.public(path),
                        path,
                        title,
                        description,
                        media_type,
                        input,
                        responses,
                    )
                    self.assembly.add_root_operation(name)
                    for field in fields:
                        self.assembly.add_field(
                            name, field.name, field.type, field.title, field.values, field.default)
                    continue
                resource, scope = ownership
                self.assembly.add_operation(
                    resource.reference,
                    scope,
                    name,
                    operation_method,
                    self.routes.public(path),
                    path,
                    title,
                    description,
                    media_type,
                    input,
                    responses,
                )
                for field in fields:
                    self.assembly.add_field(
                        name, field.name, field.type, field.title, field.values, field.default)
                if (
                    scope == SirenScope.COLLECTION
                    and path == resource.collection_path
                    and not self.routes.parameters(path)
                    and operation_method != SirenHttpMethod.GET
                ):
                    self.assembly.add_root_operation(name)

    def input(
        self, path_item: dict[str, Any], operation: dict[str, Any]
    ) -> tuple[tuple[Field, ...], InputDraft | None]:
        parameters = (*path_item.get("parameters", ()),
                      *operation.get("parameters", ()))
        parameter_index: dict[tuple[str, str], dict[str, Any]] = {}
        for parameter in parameters:
            definition = self.components.parameter(parameter)
            name = definition.get("name")
            location = definition.get("in")
            if not isinstance(name, str) or not isinstance(location, str):
                raise SirenityError(
                    "OpenAPI parameter requires string name and location")
            if location not in {"path", "query", "header", "cookie"}:
                raise SirenityError(
                    f"OpenAPI parameter location is unsupported: {location}")
            schema = definition.get("schema")
            if not isinstance(schema, dict):
                raise SirenityError(
                    f"OpenAPI parameter schema is required: {name}")
            parameter_index[name, location] = definition
        fields: list[Field] = []
        delegated: list[DelegatedInputDraft] = []
        normalized_parameters: list[ParameterInputDraft] = []
        names: set[str] = set()
        for (name, location), parameter in parameter_index.items():
            definition = self.components.schema_tree(parameter["schema"])
            if not isinstance(definition, dict):
                raise SirenityError(
                    f"OpenAPI parameter schema is required: {name}")
            if name in names:
                raise SirenityError(
                    f"OpenAPI parameters cannot share a name across locations: {name}")
            names.add(name)
            normalized_parameters.append(ParameterInputDraft(
                name=name,
                location=location,
                required=parameter.get("required") is True or location == "path",
                definition=definition,
            ))
            if location == "path":
                continue
            if location == "query":
                try:
                    fields.append(self.projection.field(name, definition))
                    continue
                except SirenityError:
                    kind = self.projection.delegated_kind(name, definition)
                    if kind is None:
                        raise
            else:
                kind = self.projection.delegated_kind(
                    name, definition) or "json"
            delegated.append(DelegatedInputDraft(
                name=name,
                location=location,
                kind=kind,
                required=parameter.get("required") is True,
                style=parameter.get(
                    "style", "simple" if location == "header" else "form"),
                explode=parameter.get("explode", location != "header"),
                allow_reserved=parameter.get("allowReserved") is True,
                definition=definition,
            ))
        body = self.components.request_body(operation.get("requestBody", {}))
        content = body.get("content", {}) if isinstance(body, dict) else {}
        if content and not isinstance(content, dict):
            raise SirenityError(
                "OpenAPI request body content must be an object")
        media_name = "application/json" if isinstance(
            content, dict) and "application/json" in content else None
        if media_name is None and isinstance(content, dict) and len(content) == 1:
            media_name = next(iter(content))
        if content and not isinstance(media_name, str):
            raise SirenityError(
                "OpenAPI request body media types are ambiguous")
        media = content.get(media_name, {}) if isinstance(
            content, dict) and media_name else {}
        if content and not isinstance(media, dict):
            raise SirenityError("OpenAPI request body media type is invalid")
        media_type = SirenMediaType.validate(
            media_name) if media_name else None
        schema = media.get("schema", {}) if isinstance(media, dict) else {}
        if content and not isinstance(schema, dict):
            raise SirenityError("OpenAPI request body schema is required")
        definition = self.components.schema_tree(schema) if content else None
        if definition is not None and not isinstance(definition, dict):
            raise SirenityError("OpenAPI request body schema is required")
        if content and media_name != "application/json":
            delegated.append(DelegatedInputDraft(
                name="body",
                location="body",
                kind=self.projection.delegated_kind(
                    "body", definition) or "json",
                required=body.get("required") is True,
                media_type=media_type,
                definition=definition,
            ))
            return tuple(fields), InputDraft(
                media_type=media_type,
                definition=definition,
                official_fields=tuple(field.name for field in fields),
                parameters=tuple(normalized_parameters),
                delegated_inputs=tuple(delegated),
            )
        if content and definition.get("type") != "object":
            raise SirenityError("OpenAPI JSON request body must be an object")
        properties = definition.get("properties", {}) if definition else {}
        if not isinstance(properties, dict):
            raise SirenityError(
                "OpenAPI JSON request body properties must be an object")
        required = definition.get("required", []) if definition else []
        if not isinstance(required, list) or any(not isinstance(name, str) for name in required):
            raise SirenityError(
                "OpenAPI JSON request body required properties must be an array of names")
        for name, value in properties.items():
            if not isinstance(name, str) or not isinstance(value, dict):
                raise SirenityError(
                    "OpenAPI JSON request body property is invalid")
            if name in names:
                raise SirenityError(
                    f"OpenAPI inputs cannot share a name across locations: {name}")
            names.add(name)
            try:
                fields.append(self.projection.field(name, value))
            except SirenityError:
                kind = self.projection.delegated_kind(name, value)
                if kind is None:
                    raise
                delegated.append(DelegatedInputDraft(
                    name=name,
                    location="body",
                    kind=kind,
                    required=name in required,
                    media_type=media_type,
                    definition=value,
                ))
        if not fields and not delegated and not normalized_parameters and not content:
            return (), None
        return tuple(fields), InputDraft(
            media_type=media_type,
            definition=definition,
            official_fields=tuple(field.name for field in fields),
            parameters=tuple(normalized_parameters),
            delegated_inputs=tuple(delegated),
        )

    def response_links(self, responses):
        values = []
        for response in responses:
            links = []
            for link in response.links:
                reference = link.operation_ref
                if reference is not None:
                    if not reference.startswith("#/paths/"):
                        raise SirenityError(
                            f"OpenAPI response link operationRef is unsupported: {reference}"
                        )
                    parts = reference[len("#/paths/"):].rsplit("/", 1)
                    if len(parts) != 2 or not parts[1]:
                        raise SirenityError(
                            f"OpenAPI response link operationRef is invalid: {reference}")
                    path = parts[0].replace("~1", "/").replace("~0", "~")
                    links.append(link.model_copy(update={
                        "operation_ref": f"{self.routes.public(path)}#{parts[1].lower()}"
                    }))
                else:
                    links.append(link)
            values.append(response.model_copy(update={"links": tuple(links)}))
        return tuple(values)
