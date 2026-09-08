from typing import Any, ClassVar

import pydantic

from sirenity.contexts.graph import (
    SirenDelegatedInput,
    SirenField,
    SirenInput,
    SirenParameterInput,
)
from sirenity.contexts.shared import (
    BaseState,
    SirenActionMethod,
    SirenHttpMethod,
    SirenityError,
    SirenMediaType,
    SirenScope,
)

from ...compatibility import SirenCompatibilityFinding
from ..values import OperationDraft
from .components import ComponentResolver
from .field_projection import OpenApiFieldProjection
from .response_projection import OpenApiResponseProjection
from .routes import RouteCatalog


class OpenApiOperationCompiler(BaseState):
    methods: ClassVar[frozenset[SirenHttpMethod]] = frozenset(
        SirenHttpMethod(value) for value in SirenActionMethod.values()
    )
    routes: RouteCatalog
    components: ComponentResolver
    projection: OpenApiFieldProjection
    responses: OpenApiResponseProjection
    findings: list[SirenCompatibilityFinding] = pydantic.Field(default_factory=list)
    operation_ids: set[str] = pydantic.Field(default_factory=set)
    operations: list[OperationDraft] = pydantic.Field(default_factory=list)
    root_operations: list[str] = pydantic.Field(default_factory=list)

    def compile(self) -> tuple[SirenCompatibilityFinding, ...]:
        for path, path_item in self.routes.paths.items():
            location = self.location("paths", path)
            if not isinstance(path_item, dict):
                self.add(
                    location,
                    "route",
                    "OpenAPI path item must be an object",
                    "Use an object-valued OpenAPI path item.",
                )
                continue
            if "$ref" in path_item:
                self.add(
                    location,
                    "component-reference",
                    f"OpenAPI path item reference is unsupported: {path}",
                    "Inline the path item in the Siren-facing contract.",
                )
                continue
            for method, operation in path_item.items():
                self.operation(path, path_item, method, operation)
        return tuple(self.findings)

    def operation(self, path: str, path_item: dict[str, Any], method: Any, operation: Any) -> None:
        if not isinstance(method, str):
            return
        method_name = method.lower()
        if method_name == "trace":
            self.unsupported_method(path, method)
            return
        try:
            operation_method = SirenHttpMethod(method.upper())
        except ValueError:
            return
        if operation_method in {SirenHttpMethod.HEAD, SirenHttpMethod.OPTIONS}:
            self.unsupported_method(path, method)
            return
        if operation_method not in self.methods or not isinstance(operation, dict):
            return
        finding_count = len(self.findings)
        location = self.location("paths", path, method_name)
        name = operation.get("operationId")
        if not isinstance(name, str) or not name:
            self.add(
                location,
                "operation-id",
                f"OpenAPI operation requires operationId: {method.upper()} {path}",
                "Provide a unique operationId.",
            )
        elif name in self.operation_ids:
            self.add(
                self.location_from(location, "operationId"),
                "operation-id",
                f"OpenAPI operationId is duplicated: {name}",
                "Use a unique operationId for every Siren action.",
            )
        else:
            self.operation_ids.add(name)
        title = operation.get("summary")
        if not isinstance(title, str) or not title:
            self.add(
                self.location_from(location, "summary"),
                "operation-summary",
                f"OpenAPI operation requires a non-empty summary: {method.upper()} {path}",
                "Provide a non-empty summary for the Siren action title.",
            )
        description = operation.get("description")
        if not isinstance(description, str) or not description:
            self.add(
                self.location_from(location, "description"),
                "operation-description",
                f"OpenAPI operation requires a non-empty description: {method.upper()} {path}",
                "Provide a non-empty description for the caller-facing operation contract.",
            )
        try:
            ownership = self.routes.ownership(path)
        except (SirenityError, ValueError) as error:
            self.add(
                self.location("paths", path),
                "route",
                str(error),
                "Use an unambiguous plural collection or entity route.",
            )
            ownership = None
        try:
            fields, input = self.input(path_item, operation)
        except (SirenityError, ValueError) as error:
            self.input_error(location, error)
            fields, input = (), None
        try:
            responses = self.response_links(self.responses.responses(operation))
        except (SirenityError, ValueError) as error:
            self.add(
                self.location_from(location, "responses"),
                "response-schema",
                str(error),
                "Use object, array-of-object, or content-free responses with resolvable local schema references.",
            )
            responses = ()
        if len(self.findings) != finding_count:
            return
        if not isinstance(name, str) or not isinstance(title, str) or not isinstance(description, str):
            return
        media_type = input.media_type if input else None
        resource, scope = ownership or (None, SirenScope.ROOT)
        self.operations.append(OperationDraft(
            resource=resource.reference if resource else None,
            scope=scope,
            name=name,
            method=operation_method,
            path=self.routes.public(path),
            source_path=path,
            title=title,
            description=description,
            media_type=media_type,
            fields=fields,
            input=input,
            responses=responses,
        ))
        if ownership is None:
            self.root_operations.append(name)
            return
        if (
            scope == SirenScope.COLLECTION
            and path == resource.collection_path
            and not self.routes.parameters(path)
            and operation_method != SirenHttpMethod.GET
        ):
            self.root_operations.append(name)

    def unsupported_method(self, path: str, method: str) -> None:
        self.add(
            self.location("paths", path, method.lower()),
            "http-method",
            f"OpenAPI operation method is unsupported: {method.upper()} {path}",
            "Use an official Siren action method: GET, POST, PUT, PATCH, or DELETE.",
        )

    def input_error(self, location: str, error: Exception) -> None:
        detail = str(error)
        if "component reference" in detail:
            category = "component-reference"
            remediation = "Use resolvable local component references."
        elif "parameter location" in detail:
            category = "parameter-location"
            remediation = "Use a path, query, header, or cookie parameter."
        elif "parameter" in detail:
            category = "parameter"
            remediation = "Provide uniquely named parameters with supported locations and schemas."
        elif "media type" in detail or "content must" in detail:
            category = "body-media-type"
            remediation = "Provide application/json or exactly one declared request media type."
        else:
            category = "body-schema"
            remediation = "Use an object-valued request body with supported fields."
        suffix = ("requestBody", "content") if category == "body-media-type" else ("parameters",)
        self.add(self.location_from(location, *suffix), category, detail, remediation)

    def add(self, location: str, category: str, detail: str, remediation: str) -> None:
        self.findings.append(SirenCompatibilityFinding(
            location=location,
            category=category,
            detail=detail,
            remediation=remediation,
        ))

    def location(self, *tokens: str) -> str:
        return "#" + "".join("/" + self.escape(token) for token in tokens)

    def location_from(self, location: str, *tokens: str) -> str:
        return location + "".join("/" + self.escape(token) for token in tokens)

    def escape(self, token: str) -> str:
        return token.replace("~", "~0").replace("/", "~1")

    def input(
        self, path_item: dict[str, Any], operation: dict[str, Any]
    ) -> tuple[tuple[SirenField, ...], SirenInput | None]:
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
        fields: list[SirenField] = []
        delegated: list[SirenDelegatedInput] = []
        normalized_parameters: list[SirenParameterInput] = []
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
            normalized_parameters.append(SirenParameterInput(
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
            delegated.append(SirenDelegatedInput(
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
            delegated.append(SirenDelegatedInput(
                name="body",
                location="body",
                kind=self.projection.delegated_kind(
                    "body", definition) or "json",
                required=body.get("required") is True,
                media_type=media_type,
                definition=definition,
            ))
            return tuple(fields), SirenInput(
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
                delegated.append(SirenDelegatedInput(
                    name=name,
                    location="body",
                    kind=kind,
                    required=name in required,
                    media_type=media_type,
                    definition=value,
                ))
        if not fields and not delegated and not normalized_parameters and not content:
            return (), None
        return tuple(fields), SirenInput(
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
