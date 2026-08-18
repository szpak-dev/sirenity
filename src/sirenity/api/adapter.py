from collections.abc import Mapping
from typing import Any

from ..contexts.runtime.adapter import SirenAdapter, SirenAdapterProfile
from ..contexts.runtime.adapter.values import SirenAdapterRoute
from ..contexts.shared import SirenityError
from .siren import siren


def siren_adapter(
    openapi: Mapping[str, Any],
    *,
    source_path: str = "/",
    public_path: str = "/",
    profiles: tuple[SirenAdapterProfile, ...] = (),
) -> SirenAdapter:
    """Compile a framework-neutral boundary for operation-aware Siren HTTP responses.

    Call this once after framework routes are registered. The adapter compiles OpenAPI once and
    retains a route catalogue mapping both the framework's source mount and the public Siren mount
    to operation IDs. Consumers neither inspect the engine graph nor parse OpenAPI.

    Matching is independent of OpenAPI declaration order. Candidates require the same segment count;
    at each position a literal outranks a parameter, for both source and public mounts. Parameter values
    are percent-decoded only after structural matching, so an encoded value cannot become a literal route.
    Same-method templates with indistinguishable parameter shapes fail adapter construction explicitly.

    Default payloads remain extension-free official Siren. Pass explicit adapter profiles to enrich a
    fresh serialized document from public normalized operation metadata. `SirenStructuredFormProfile`
    adds a versioned URI-namespaced control extension for delegated structured inputs without changing
    official scalar fields:

    ```python
    from sirenity import SirenStructuredFormProfile, siren_adapter

    adapter = siren_adapter(
        api.get_openapi_schema(),
        profiles=(SirenStructuredFormProfile(),),
    )
    ```

    ```python
    from sirenity import SirenAdapterPolicy, SirenAdapterRequest, siren_adapter

    adapter = siren_adapter(api.get_openapi_schema(), source_path="/api", public_path="/siren")
    response = adapter.respond(SirenAdapterRequest(
        operation_id="get_article",
        status=200,
        result={"article_id": "42", "title": "Adapter boundaries"},
        base_url="https://api.example.com",
        path_values={"article_id": "42"},
        policy=SirenAdapterPolicy(capabilities=frozenset({"get_article", "update_article"})),
    ))

    assert response.media_type == "application/vnd.siren+json"
    ```

    The result must come from an operation the application has already executed; `respond()` never
    dispatches application code. Pass `operation_id` directly when the framework exposes it, or pass
    `method` and `path` for catalogue resolution. Capability sets are explicit `SirenAdapterPolicy`
    inputs and are never inferred from result identifiers. The compiled graph supplies deterministic
    defaults for an exact root entry point, collection arrays, objects on exact resource routes, and
    command objects on subcommand routes; policy `representation` overrides exceptional operations.
    For collection results, `item_titles` supplies one application-owned title per item. Titles and
    item-specific capability sets are independently validated against result order; an empty result
    needs neither.

    Declared exact, ranged, and default error responses use their compiled schema and media type.
    When a framework returns an undeclared status from 400 through 599, the adapter instead preserves
    its mapping, list, scalar, or empty result in a generic Siren error document. A declared status with
    an incompatible runtime media type also uses this fallback; successful responses remain strict.

    An exact root operation uses the root projector and supplies `class: ["api", "entry-point"]`,
    discovery links, and permitted root actions. Executed mapping members become document properties;
    compiled OpenAPI `info.version` wins a `version` collision, and the policy title continues to
    override `info.title`. Use `representation="command"` when that operation is intentionally a
    command result.

    For Django Ninja and Ninja Extra, `SirenDjangoMiddleware` negotiates source routes directly. When
    source and public mounts differ, a matched public route is rewritten to its compiled source route
    before Django resolution, executed once, then restored before Siren projection. Unmatched routes
    are never rewritten.

    The bridge keeps Django optional by importing it only while handling a matched response. It transforms
    matched `application/json`, `+json`, and content-free responses. Accept ranges use quality and specificity;
    an exact range overrides a wildcard for that representation, equal explicit preferences use client
    order, and missing or wildcard-only Accept values retain JSON. Media types are case-insensitive and
    `q=0` forbids Siren.
    Unmatched routes, non-JSON content, streams, files, redirects, 304 responses, and already-Siren
    responses pass through without projection. Non-Siren requests receive the original response object, with
    `Vary: Accept` merged when that matched response was eligible for representation negotiation.

    A transformed response merges `Accept` into `Vary`, retains cookies plus semantic and security
    headers, and removes source-byte validators, digests, encodings, ranges, and framing. Put Django's
    `ConditionalGetMiddleware` before `SirenDjangoMiddleware` so response processing validates the final
    Siren bytes; a 304 produced downstream is passed through because it has no representation to project.
    Unmatched errors also pass through because the bridge does not guess API ownership from a URL prefix.
    Direct middleware construction receives an explicit authorization policy; the standard Django
    loader uses `SirenAllowAllPolicy` when `MODWIRE_SIREN["POLICY"]` is absent:

    ```python
    from sirenity import SirenAdapterPolicy, SirenDjangoMiddleware

    django_adapter = siren_adapter(
        api.get_openapi_schema(),
        source_path="/api",
        public_path="/api",
    )

    class Capabilities:
        def select(self, operation_id, status, request, result):
            permitted = frozenset({operation_id}) if operation_id is not None else frozenset()
            return SirenAdapterPolicy(capabilities=permitted)

    middleware = SirenDjangoMiddleware(
        get_response=django_handler,
        adapter=django_adapter,
        policy=Capabilities(),
    )
    ```
    """

    try:
        engine = siren(openapi, source_path=source_path,
                       public_path=public_path)
        source = source_path.rstrip("/") or "/"
        public = public_path.rstrip("/") or "/"
        source_routes = {}
        for path, path_item in openapi.get("paths", {}).items():
            if not isinstance(path, str) or not isinstance(path_item, Mapping):
                continue
            for method, definition in path_item.items():
                if not isinstance(method, str) or not isinstance(definition, Mapping):
                    continue
                operation_id = definition.get("operationId")
                if isinstance(operation_id, str):
                    source_routes[operation_id, method.upper()] = path
        routes = []
        for operation in engine.api.operations:
            public_route = operation.route.path
            if public == "/":
                suffix = public_route
            elif public_route == public:
                suffix = "/"
            else:
                suffix = public_route[len(public):]
            source_route = source_routes.get(
                (operation.name, operation.method),
                suffix if source == "/" else source +
                ("" if suffix == "/" else suffix),
            )
            routes.append(SirenAdapterRoute(
                source_path=source_route,
                public_path=public_route,
                method=operation.method,
                operation_id=operation.name,
            ))
        return SirenAdapter(engine=engine, routes=tuple(routes), profiles=profiles)
    except Exception as error:
        raise SirenityError(
            f"Invalid or unsupported Siren adapter contract: {error}") from error
