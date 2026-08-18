import re
from collections.abc import Mapping
from urllib.parse import quote, unquote

from pydantic import JsonValue, model_validator

from sirenity.contexts.shared import BaseState, SirenityError

from ...document import SirenDocument, SirenLink
from ...engine import SirenEngine
from ...operation_input import SirenOperationInput
from ...request import SirenResponseContext
from ..contracts import SirenAdapterProfile
from ..values import SirenAdapterMatch, SirenAdapterRequest, SirenAdapterResponse, SirenAdapterRoute


class SirenAdapter(BaseState):
    """Project already-executed framework results through a startup-compiled Siren engine.

    Use `match()` when a framework exposes only its HTTP method and path. Use `respond()` after the
    application operation has executed exactly once. The adapter preserves semantic response headers
    while removing validators and content metadata tied to the source bytes, then returns an HTTP-ready
    payload with the official Siren media type.

    Route resolution compares exact segment counts and ranks matching templates position by position,
    with literal segments ahead of parameters. Source and public templates use the same ranking. Adapter
    construction rejects same-method templates that become identical after parameter names are removed.
    Explicit profiles form a validated ordered pipeline over fresh serialized payloads and deep-copied
    public operation-input values; the cached engine graph remains immutable across requests.
    """

    engine: SirenEngine
    routes: tuple[SirenAdapterRoute, ...]
    profiles: tuple[SirenAdapterProfile, ...] = ()

    @model_validator(mode="after")
    def validate_routes(self) -> "SirenAdapter":
        profile_types = tuple(type(profile) for profile in self.profiles)
        if len(set(profile_types)) != len(profile_types):
            raise SirenityError("Siren adapter profile types must be unique")
        if any(not isinstance(profile, SirenAdapterProfile) for profile in self.profiles):
            raise SirenityError(
                "Siren adapter profiles must implement SirenAdapterProfile")
        templates = {}
        for route in self.routes:
            for template in dict.fromkeys((route.source_path, route.public_path)):
                parts = template.strip(
                    "/").split("/") if template != "/" else []
                canonical_parts = tuple(
                    "{}" if part.startswith(
                        "{") and part.endswith("}") else part
                    for part in parts
                )
                canonical = "/" + "/".join(canonical_parts)
                key = (route.method, canonical)
                existing = templates.get(key)
                if existing is not None:
                    raise SirenityError(
                        f"Ambiguous Siren adapter templates for {route.method} {canonical}: "
                        f"{existing[0]!r} ({existing[1]}) and {route.operation_id!r} ({template})"
                    )
                templates[key] = (route.operation_id, template)
        return self

    def match(self, method: str, path: str) -> SirenAdapterMatch | None:
        normalized = "/" + path.strip("/") if path.strip("/") else "/"
        selected = None
        selected_specificity = None
        for route in self.routes:
            if route.method != method.upper():
                continue
            for template in dict.fromkeys((route.source_path, route.public_path)):
                template_parts = template.strip(
                    "/").split("/") if template != "/" else []
                path_parts = normalized.strip(
                    "/").split("/") if normalized != "/" else []
                if len(template_parts) != len(path_parts):
                    continue
                values = {}
                matches = True
                for expected, actual in zip(template_parts, path_parts, strict=True):
                    if expected.startswith("{") and expected.endswith("}"):
                        values[expected[1:-1]] = actual
                    elif expected != actual:
                        matches = False
                        break
                if matches:
                    specificity = tuple(
                        int(not (part.startswith("{") and part.endswith("}")))
                        for part in template_parts
                    )
                    if selected_specificity is None or specificity > selected_specificity:
                        selected = SirenAdapterMatch(
                            operation_id=route.operation_id,
                            path_values={name: unquote(
                                value) for name, value in values.items()},
                        )
                        selected_specificity = specificity
        return selected

    def dispatch_path(self, method: str, path: str) -> str | None:
        match = self.match(method, path)
        if match is None:
            return None
        routes = [
            route for route in self.routes if route.operation_id == match.operation_id]
        if len(routes) != 1:
            raise SirenityError(
                f"Siren adapter operation requires exactly one route: {match.operation_id}"
            )
        route = routes[0]
        public_path = self.render_path(route.public_path, match.path_values)
        normalized = "/" + path.strip("/") if path.strip("/") else "/"
        normalized_public = "/" + \
            public_path.strip("/") if public_path.strip("/") else "/"
        if normalized != normalized_public:
            return None
        source_path = self.render_path(route.source_path, match.path_values)
        if path.endswith("/") and not source_path.endswith("/"):
            source_path += "/"
        return source_path

    def render_path(self, template: str, values: Mapping[str, JsonValue]) -> str:
        return re.sub(
            r"\{([^}]+)\}",
            lambda matched: quote(str(values[matched.group(1)]), safe=""),
            template,
        )

    def respond(self, request: SirenAdapterRequest) -> SirenAdapterResponse:
        try:
            match = None
            if request.operation_id is None and request.method is not None and request.path is not None:
                match = self.match(request.method, request.path)
            operation_id = request.operation_id or (
                match.operation_id if match is not None else None)
            path_values = dict(match.path_values if match is not None else {}) | dict(
                request.path_values)
            if operation_id is None:
                document = self.error(request)
            else:
                capabilities = request.policy.capabilities
                if request.policy.all_capabilities:
                    capabilities = self.capabilities(operation_id)
                context = SirenResponseContext(
                    operation_id=operation_id,
                    status=request.status,
                    result=request.result,
                    base_url=request.base_url,
                    title=request.policy.title,
                    media_type=request.media_type,
                    representation=request.policy.representation,
                    path_values=path_values,
                    query=request.query,
                    capabilities=capabilities,
                    item_titles=request.policy.item_titles,
                    item_capabilities=request.policy.item_capabilities,
                    relationships=request.policy.relationships,
                )
                if request.status >= 400 and not self.engine.has_response(context):
                    document = self.engine.project_error(
                        context, request.request_url)
                else:
                    document = self.engine.project_response(context)
            headers = {
                name: value
                for name, value in request.headers.items()
                if name.lower() not in {
                    "accept-ranges",
                    "content-digest",
                    "content-encoding",
                    "content-length",
                    "content-md5",
                    "content-range",
                    "content-type",
                    "digest",
                    "etag",
                    "last-modified",
                    "repr-digest",
                    "trailer",
                    "transfer-encoding",
                }
            }
            payload = document.model_dump(
                by_alias=True, mode="json", exclude_none=True)
            if self.profiles and operation_id is not None:
                operation_inputs: dict[str, SirenOperationInput | None] = {}
                for route in self.routes:
                    if route.operation_id not in operation_inputs:
                        value = self.engine.operation_input(route.operation_id)
                        operation_inputs[route.operation_id] = (
                            value.model_copy(
                                deep=True) if value is not None else None
                        )
                operation_input = operation_inputs.get(operation_id)
                for profile in self.profiles:
                    payload = dict(profile.apply(
                        operation_id=operation_id,
                        operation_input=(
                            operation_input.model_copy(deep=True)
                            if operation_input is not None
                            else None
                        ),
                        operation_inputs={
                            name: value.model_copy(
                                deep=True) if value is not None else None
                            for name, value in operation_inputs.items()
                        },
                        document=payload,
                        context=context,
                    ))
            return SirenAdapterResponse(
                status=request.status,
                payload=payload,
                headers=headers,
            )
        except Exception as error:
            raise SirenityError("Siren adapter response failed") from error

    def capabilities(self, operation_id: str) -> frozenset[str]:
        operations = [
            operation for operation in self.engine.api.operations if operation.name == operation_id]
        if len(operations) != 1:
            raise SirenityError(
                f"Siren response references unknown operation: {operation_id}")
        operation = operations[0]
        if operation.resource is None:
            return frozenset(self.engine.api.root.operations)
        resources = [
            resource for resource in self.engine.api.resources
            if resource.reference == operation.resource
        ]
        if len(resources) != 1:
            raise SirenityError(
                f"Siren operation references unknown resource: {operation_id}")
        resource = resources[0]
        return frozenset((*resource.collection_operations, *resource.entity_operations))

    def error(self, request: SirenAdapterRequest) -> SirenDocument:
        if request.status < 400:
            raise SirenityError(
                "An unmatched successful response cannot be projected")
        properties = {"status": request.status}
        if isinstance(request.result, dict):
            properties = dict(request.result) | properties
        elif isinstance(request.result, list):
            properties["errors"] = request.result
        elif request.result is not None:
            properties["result"] = request.result
        links = ()
        if request.request_url is not None:
            links = (SirenLink(rel=("self",),
                     title=request.policy.title, href=request.request_url),)
        return SirenDocument(
            class_=("error",),
            title=request.policy.title,
            properties=properties,
            links=links or None,
        )
