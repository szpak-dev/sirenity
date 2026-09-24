import re
from dataclasses import dataclass
from typing import ClassVar

from pydantic import JsonValue
from wireup import injectable

from ....graph import (
    SirenDelegatedInput,
    SirenField,
    SirenInput,
    SirenParameterInput,
)
from ....shared import (
    SirenActionMethod,
    SirenHttpMethod,
    SirenityError,
    SirenMediaType,
    SirenScope,
)
from ... import SirenCompatibilityFinding, SirenDiagnostics
from ..values.compilation_request import OpenApiCompilationRequest
from ..values.normalized import NormalizedOpenApi
from ..values.operation_draft import OperationDraft
from ..values.response_draft import ResponseDraft
from .components import ComponentResolver
from .field_projection import OpenApiFieldProjection
from .response_projection import OpenApiResponseProjection
from .routes import RouteCatalog


@injectable
@dataclass(frozen=True)
class OpenApiOperationCompiler:
    methods: ClassVar[frozenset[SirenHttpMethod]] = frozenset(
        SirenHttpMethod(value) for value in SirenActionMethod.values()
    )
    routes: RouteCatalog
    components: ComponentResolver
    projection: OpenApiFieldProjection
    responses: OpenApiResponseProjection

    def compile(self, request: OpenApiCompilationRequest) -> NormalizedOpenApi | SirenDiagnostics:
        findings: list[SirenCompatibilityFinding] = []
        operation_ids: set[str] = set()
        operations: list[OperationDraft] = []
        root_operations: list[str] = []
        info = request.document["info"]
        for member in ("title", "version"):
            if not info[member]:
                self.add(
                    findings,
                    f"#/info/{member}",
                    "metadata",
                    f"OpenAPI info requires a non-empty {member}",
                    f"Provide a non-empty info.{member} value.",
                )
        single_object_paths = self.responses.single_object_paths(request)
        for path, path_item in request.paths.items():
            location = self.location(("paths", path))
            if "$ref" in path_item:
                self.add(
                    findings,
                    location,
                    "component-reference",
                    f"OpenAPI path item reference is unsupported: {path}",
                    "Inline the path item in the Siren-facing contract.",
                )
                continue
            for method, operation in path_item.items():
                self.operation(
                    request,
                    single_object_paths,
                    path,
                    path_item,
                    method,
                    operation,
                    findings,
                    operation_ids,
                    operations,
                    root_operations,
                )
        self.routes.validate_paths(request)
        resources = tuple(
            resource.model_copy(
                update={
                    "collection_path": self.routes.public(request, resource.collection_path),
                    "entity_path": (
                        self.routes.public(request, resource.entity_path) if resource.entity_path else None
                    ),
                }
            )
            for resource in self.routes.resources(request, single_object_paths)
        )
        if findings:
            return SirenDiagnostics(findings=tuple(findings))
        return NormalizedOpenApi(
            root_path=request.public_path,
            root_title=info["title"],
            root_version=info["version"],
            resources=resources,
            operations=tuple(operations),
            root_operations=tuple(root_operations),
        )

    def operation(
        self,
        request: OpenApiCompilationRequest,
        single_object_paths: frozenset[str],
        path: str,
        path_item: dict[str, JsonValue],
        method: str,
        operation: dict[str, JsonValue],
        findings: list[SirenCompatibilityFinding],
        operation_ids: set[str],
        operations: list[OperationDraft],
        root_operations: list[str],
    ) -> None:
        method_name = method.lower()
        if method_name == "trace":
            self.unsupported_method(findings, path, method)
            return
        if method_name not in {value.value.lower() for value in self.methods} | {"head", "options"}:
            return
        operation_method = SirenHttpMethod(method.upper())
        if operation_method in {SirenHttpMethod.HEAD, SirenHttpMethod.OPTIONS}:
            self.unsupported_method(findings, path, method)
            return
        if operation_method not in self.methods:
            return
        finding_count = len(findings)
        location = self.location(("paths", path, method_name))
        name = operation.get("operationId")
        if not name:
            self.add(
                findings,
                location,
                "operation-id",
                f"OpenAPI operation requires operationId: {method.upper()} {path}",
                "Provide a unique operationId.",
            )
        elif name in operation_ids:
            self.add(
                findings,
                self.location_from(location, ("operationId",)),
                "operation-id",
                f"OpenAPI operationId is duplicated: {name}",
                "Use a unique operationId for every Siren action.",
            )
        else:
            operation_ids.add(name)
        title = operation.get("summary")
        if not title:
            self.add(
                findings,
                self.location_from(location, ("summary",)),
                "operation-summary",
                f"OpenAPI operation requires a non-empty summary: {method.upper()} {path}",
                "Provide a non-empty summary for the Siren action title.",
            )
        description = operation.get("description")
        if not description:
            self.add(
                findings,
                self.location_from(location, ("description",)),
                "operation-description",
                f"OpenAPI operation requires a non-empty description: {method.upper()} {path}",
                "Provide a non-empty description for the caller-facing operation contract.",
            )
        ownership = self.routes.ownership(request, single_object_paths, path)
        fields, input = self.input(request, path_item, operation)
        responses = self.response_links(request, self.responses.responses(request, operation))
        if len(findings) != finding_count:
            return
        media_type = input.media_type if input else None
        resource, scope = ownership or (None, SirenScope.ROOT)
        operations.append(
            OperationDraft(
                resource=resource.reference if resource else "",
                scope=scope,
                name=name,
                method=operation_method,
                path=self.routes.public(request, path),
                source_path=path,
                title=title,
                description=description,
                fields=fields,
                responses=responses,
                **({"media_type": media_type} if media_type is not None else {}),
                **({"input": input} if input is not None else {}),
            )
        )
        if ownership is None:
            root_operations.append(name)
            return
        if (
            scope == SirenScope.COLLECTION
            and path == resource.collection_path
            and not self.routes.parameters(path)
            and operation_method != SirenHttpMethod.GET
        ):
            root_operations.append(name)

    def unsupported_method(self, findings: list[SirenCompatibilityFinding], path: str, method: str) -> None:
        self.add(
            findings,
            self.location(("paths", path, method.lower())),
            "http-method",
            f"OpenAPI operation method is unsupported: {method.upper()} {path}",
            "Use an official Siren action method: GET, POST, PUT, PATCH, or DELETE.",
        )

    def add(
        self,
        findings: list[SirenCompatibilityFinding],
        location: str,
        category: str,
        detail: str,
        remediation: str,
    ) -> None:
        findings.append(
            SirenCompatibilityFinding(
                location=location,
                category=category,
                detail=detail,
                remediation=remediation,
            )
        )

    def location(self, tokens: tuple[str, ...]) -> str:
        return "#" + "".join("/" + self.escape(token) for token in tokens)

    def location_from(self, location: str, tokens: tuple[str, ...]) -> str:
        return location + "".join("/" + self.escape(token) for token in tokens)

    def escape(self, token: str) -> str:
        return token.replace("~", "~0").replace("/", "~1")

    def input(
        self,
        request: OpenApiCompilationRequest,
        path_item: dict[str, JsonValue],
        operation: dict[str, JsonValue],
    ) -> tuple[tuple[SirenField, ...], SirenInput | None]:
        parameters = (*path_item.get("parameters", ()), *operation.get("parameters", ()))
        parameter_index: dict[tuple[str, str], dict[str, JsonValue]] = {}
        for parameter in parameters:
            definition = self.components.parameter(request, parameter)
            name = definition["name"]
            location = definition["in"]
            if location not in {"path", "query", "header", "cookie"}:
                raise SirenityError(f"OpenAPI parameter location is unsupported: {location}")
            parameter_index[name, location] = definition
        fields: list[SirenField] = []
        delegated: list[SirenDelegatedInput] = []
        normalized_parameters: list[SirenParameterInput] = []
        names: set[str] = set()
        for (name, location), parameter in parameter_index.items():
            definition = self.components.schema_tree(request, parameter["schema"], ())
            if name in names:
                raise SirenityError(f"OpenAPI parameters cannot share a name across locations: {name}")
            names.add(name)
            normalized_parameters.append(
                SirenParameterInput(
                    name=name,
                    location=location,
                    required=parameter.get("required") is True or location == "path",
                    definition=definition,
                )
            )
            if location == "path":
                continue
            if location == "query":
                kind = self.projection.delegated_kind(request, name, definition)
                if kind is None:
                    fields.append(self.projection.field(request, name, definition))
                    continue
            else:
                kind = self.projection.delegated_kind(request, name, definition) or "json"
            delegated.append(
                SirenDelegatedInput(
                    name=name,
                    location=location,
                    kind=kind,
                    required=parameter.get("required") is True,
                    style=parameter.get("style", "simple" if location == "header" else "form"),
                    explode=parameter.get("explode", location != "header"),
                    allow_reserved=parameter.get("allowReserved") is True,
                    definition=definition,
                )
            )
        body = self.components.request_body(request, operation.get("requestBody", {}))
        content = body.get("content", {})
        media_name = "application/json" if "application/json" in content else None
        if media_name is None and len(content) == 1:
            media_name = next(iter(content))
        if content and media_name is None:
            raise SirenityError("OpenAPI request body media types are ambiguous")
        media = content.get(media_name, {}) if media_name else {}
        media_type = SirenMediaType.validate(media_name) if media_name else None
        schema = media.get("schema", {})
        definition = self.components.schema_tree(request, schema, ()) if content else {}
        if content and media_name != "application/json":
            delegated.append(
                SirenDelegatedInput(
                    name="body",
                    location="body",
                    kind=self.projection.delegated_kind(request, "body", definition) or "json",
                    required=body.get("required") is True,
                    media_type=media_type,
                    definition=definition,
                )
            )
            return tuple(fields), SirenInput(
                media_type=media_type,
                definition=definition,
                official_fields=tuple(field.name for field in fields),
                parameters=tuple(normalized_parameters),
                delegated_inputs=tuple(delegated),
            )
        if content and definition.get("type") != "object":
            raise SirenityError("OpenAPI JSON request body must be an object")
        properties = definition.get("properties", {})
        required = definition.get("required", [])
        for name, value in properties.items():
            if name in names:
                raise SirenityError(f"OpenAPI inputs cannot share a name across locations: {name}")
            names.add(name)
            kind = self.projection.delegated_kind(request, name, value)
            if kind is None:
                fields.append(self.projection.field(request, name, value))
            else:
                delegated.append(
                    SirenDelegatedInput(
                        name=name,
                        location="body",
                        kind=kind,
                        required=name in required,
                        media_type=media_type,
                        definition=value,
                    )
                )
        if not fields and not delegated and not normalized_parameters and not content:
            return (), None
        return tuple(fields), SirenInput(
            definition=definition,
            official_fields=tuple(field.name for field in fields),
            parameters=tuple(normalized_parameters),
            delegated_inputs=tuple(delegated),
            **({"media_type": media_type} if media_type is not None else {}),
        )

    def response_links(
        self,
        request: OpenApiCompilationRequest,
        responses: tuple[ResponseDraft, ...],
    ) -> tuple[ResponseDraft, ...]:
        values: list[ResponseDraft] = []
        for response in responses:
            links = []
            for link in response.links:
                reference = link.operation_ref
                if reference is not None:
                    links.append(
                        link.model_copy(update={"operation_ref": self.operation_reference(request, reference)})
                    )
                else:
                    links.append(link)
            continuations = []
            for continuation in response.continuations:
                target = continuation.target
                if target.kind == "operation_ref":
                    target = target.model_copy(update={"value": self.operation_reference(request, target.value)})
                continuations.append(continuation.model_copy(update={"target": target}))
            values.append(response.model_copy(update={"links": tuple(links), "continuations": tuple(continuations)}))
        return tuple(values)

    def operation_reference(self, request: OpenApiCompilationRequest, reference: str) -> str:
        if not reference.startswith("#/paths/"):
            raise SirenityError(f"OpenAPI response link operationRef is unsupported: {reference}")
        parts = reference[len("#/paths/") :].rsplit("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise SirenityError(f"OpenAPI response link operationRef is invalid: {reference}")
        if re.search(r"~(?:[^01]|$)", parts[0]):
            raise SirenityError(f"OpenAPI response link operationRef is invalid: {reference}")
        path = parts[0].replace("~1", "/").replace("~0", "~")
        return f"{self.routes.public(request, path)}#{parts[1].lower()}"
