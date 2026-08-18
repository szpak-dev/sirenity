from typing import Any

from pydantic import Field

from sirenity.contexts.shared import BaseState, SirenActionMethod, SirenHttpMethod, SirenityError

from ...compatibility import SirenCompatibilityFinding
from .components import ComponentResolver
from .field_projection import OpenApiFieldProjection
from .response_projection import OpenApiResponseProjection
from .routes import RouteCatalog


class OpenApiCompatibilityInspection(BaseState):
    components: ComponentResolver
    projection: OpenApiFieldProjection
    responses: OpenApiResponseProjection
    routes: RouteCatalog
    findings: list[SirenCompatibilityFinding] = Field(default_factory=list)
    operation_ids: set[str] = Field(default_factory=set)

    def inspect(self) -> tuple[SirenCompatibilityFinding, ...]:
        for path, path_item in self.routes.paths.items():
            self.path(path, path_item)
        return tuple(self.findings)

    def path(self, path: str, path_item: Any) -> None:
        location = self.location("paths", path)
        if not isinstance(path_item, dict):
            self.add(
                location,
                "route",
                "OpenAPI path item must be an object",
                "Use an object-valued OpenAPI path item.",
            )
            return
        if "$ref" in path_item:
            self.add(
                location,
                "component-reference",
                f"OpenAPI path item reference is unsupported: {path}",
                "Inline the path item in the Siren-facing contract.",
            )
            return
        for method, operation in path_item.items():
            self.operation(path, path_item, method, operation)

    def operation(self, path: str, path_item: dict[str, Any], method: Any, operation: Any) -> None:
        if not isinstance(method, str):
            return
        method_name = method.lower()
        if method_name == "trace":
            self.add(
                self.location("paths", path, method_name),
                "http-method",
                f"OpenAPI operation method is unsupported: TRACE {path}",
                "Use an official Siren action method: GET, POST, PUT, PATCH, or DELETE.",
            )
            return
        try:
            operation_method = SirenHttpMethod(method.upper())
        except ValueError:
            return
        if operation_method in {SirenHttpMethod.HEAD, SirenHttpMethod.OPTIONS}:
            self.add(
                self.location("paths", path, method_name),
                "http-method",
                f"OpenAPI operation method is unsupported: {method.upper()} {path}",
                "Use an official Siren action method: GET, POST, PUT, PATCH, or DELETE.",
            )
            return
        supported_methods = {SirenHttpMethod(
            value) for value in SirenActionMethod.values()}
        if operation_method not in supported_methods or not isinstance(operation, dict):
            return
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
                self.location("paths", path, method_name, "operationId"),
                "operation-id",
                f"OpenAPI operationId is duplicated: {name}",
                "Use a unique operationId for every Siren action.",
            )
        else:
            self.operation_ids.add(name)
        try:
            self.routes.ownership(path)
        except ValueError as error:
            self.add(
                self.location("paths", path),
                "route",
                str(error),
                "Use an unambiguous plural collection or entity route.",
            )
        self.parameters(path_item.get("parameters", ()),
                        self.location("paths", path, "parameters"))
        self.parameters(operation.get("parameters", ()), self.location(
            "paths", path, method_name, "parameters"))
        self.request_body(operation, location)
        self.response_descriptors(operation, location)

    def response_descriptors(self, operation: dict[str, Any], location: str) -> None:
        try:
            self.responses.responses(operation)
        except (SirenityError, ValueError) as error:
            self.add(
                self.location_from(location, "responses"),
                "response-schema",
                str(error),
                "Use object, array-of-object, or content-free responses with resolvable local schema references.",
            )

    def parameters(self, parameters: Any, location: str) -> None:
        if not isinstance(parameters, (list, tuple)):
            return
        for index, parameter in enumerate(parameters):
            pointer = self.location_from(location, str(index))
            try:
                definition = self.components.parameter(parameter)
            except ValueError as error:
                self.add(pointer, "component-reference", str(error),
                         "Use a resolvable local component reference.")
                continue
            name = definition.get("name")
            parameter_location = definition.get("in")
            if not isinstance(name, str) or not isinstance(parameter_location, str):
                self.add(
                    pointer,
                    "parameter",
                    "OpenAPI parameter requires string name and location",
                    "Provide string name and in members.",
                )
                continue
            if parameter_location == "path":
                continue
            if parameter_location in {"header", "cookie"}:
                continue
            if parameter_location != "query":
                self.add(
                    pointer,
                    "parameter-location",
                    f"OpenAPI parameter location is unsupported: {parameter_location}",
                    "Use a path parameter or an optional query parameter.",
                )
                continue
            schema = definition.get("schema")
            if not isinstance(schema, dict):
                self.add(
                    self.location_from(pointer, "schema"),
                    "field-schema",
                    f"OpenAPI parameter schema is required: {name}",
                    "Use an optional scalar field schema that maps to an official Siren field type.",
                )
                continue
            self.field(name, schema, self.location_from(pointer, "schema"))

    def request_body(self, operation: dict[str, Any], location: str) -> None:
        body_location = self.location_from(location, "requestBody")
        try:
            body = self.components.request_body(
                operation.get("requestBody", {}))
        except ValueError as error:
            self.add(body_location, "component-reference", str(error),
                     "Use a resolvable local component reference.")
            return
        content = body.get("content", {}) if isinstance(body, dict) else {}
        if not content:
            return
        content_location = self.location_from(body_location, "content")
        if not isinstance(content, dict):
            self.add(
                content_location,
                "body-media-type",
                "OpenAPI request body content must be an object",
                "Use an object-valued content map.",
            )
            return
        media_name = "application/json" if "application/json" in content else None
        if media_name is None and len(content) == 1:
            media_name = next(iter(content))
        if not isinstance(media_name, str):
            self.add(
                content_location,
                "body-media-type",
                "OpenAPI request body media types are ambiguous",
                "Provide application/json or exactly one declared request media type.",
            )
            return
        media = content.get(media_name)
        if not isinstance(media, dict):
            self.add(
                self.location_from(content_location, media_name),
                "body-media-type",
                "OpenAPI request body media type is invalid",
                "Use an object-valued media type entry.",
            )
            return
        if media_name != "application/json":
            return
        media_location = self.location_from(content_location, media_name)
        schema = media.get("schema", {})
        schema_location = self.location_from(media_location, "schema")
        if not isinstance(schema, dict):
            self.add(
                schema_location,
                "body-schema",
                "OpenAPI request body schema is required",
                "Use an object-valued application/json schema.",
            )
            return
        try:
            definition = self.components.schema(schema)
        except ValueError as error:
            self.add(schema_location, "component-reference", str(error),
                     "Use a resolvable local component reference.")
            return
        if definition.get("type") != "object":
            self.add(
                schema_location,
                "body-schema",
                "OpenAPI JSON request body must be an object",
                "Use an object-valued application/json schema.",
            )
            return
        properties = definition.get("properties", {})
        if not isinstance(properties, dict):
            self.add(
                self.location_from(schema_location, "properties"),
                "body-schema",
                "OpenAPI JSON request body properties must be an object",
                "Use object properties for Siren fields.",
            )
            return
        for name, value in properties.items():
            if not isinstance(name, str) or not isinstance(value, dict):
                self.add(
                    self.location_from(schema_location, "properties"),
                    "field-schema",
                    "OpenAPI JSON request body property is invalid",
                    "Use named object properties with scalar schemas.",
                )
                continue
            self.field(name, value, self.location_from(
                schema_location, "properties", name))

    def field(self, name: str, schema: dict[str, Any], location: str) -> None:
        try:
            self.projection.field(name, schema)
        except (SirenityError, ValueError):
            if self.projection.delegated_kind(name, schema) is not None:
                return
            self.add(
                location,
                "field-schema",
                f"OpenAPI field schema is unsupported: {name}",
                "Use a flat scalar schema that maps to an official Siren field type.",
            )

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
