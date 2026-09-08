"""Django integration.

<!-- docs:order=40 -->
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..contexts.runtime.adapter import SirenDjangoMiddleware
from ..contexts.runtime.configuration import SirenConfiguration
from ..contexts.shared import SirenityError
from .configuration import siren_configuration


def siren_pagination(
    route: Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]],
    path: str = "",
    *,
    response: type[Any],
    operation_id: str,
    continuation: Mapping[str, str],
    status: int = 200,
    **operation: object,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare one typed paginated Django Ninja or Ninja Extra operation.

    Pass ``api.get`` for Django Ninja or ``http_get`` for Ninja Extra. The response model and
    continuation mapping produce one successful response containing a standard OpenAPI ``next``
    Link Object. The operation ID is declared once and reused as the link target. Sirenity's normal
    startup compilation validates every mapped query parameter and response property.

    ```python
    from ninja import Schema

    from sirenity import siren_pagination

    class ArticlePage(Schema):
        items: list[Article]
        has_more: bool
        next_offset: int
        limit: int

    @siren_pagination(
        api.get,
        "/api/articles",
        response=ArticlePage,
        operation_id="list_articles",
        continuation={"offset": "next_offset", "limit": "limit"},
        summary="List articles",
        description="List one page of articles.",
    )
    def list_articles(request, offset: int = 0, limit: int = 20):
        return ArticlePage(items=[], has_more=False, next_offset=0, limit=limit)
    ```
    """

    if not callable(route):
        raise SirenityError("Siren pagination route must be callable")
    if not isinstance(path, str):
        raise SirenityError("Siren pagination path must be a string")
    if not isinstance(response, type):
        raise SirenityError("Siren pagination response model is required")
    if not isinstance(operation_id, str) or not operation_id:
        raise SirenityError("Siren pagination operation_id must be non-empty")
    if isinstance(status, bool) or not isinstance(status, int) or not 200 <= status < 300:
        raise SirenityError("Siren pagination status must be a successful integer status")
    if not isinstance(continuation, Mapping) or not continuation or any(
        not isinstance(query, str)
        or not query
        or not isinstance(property_name, str)
        or not property_name
        for query, property_name in continuation.items()
    ):
        raise SirenityError("Siren pagination continuation must map query names to response properties")
    if len(set(continuation.values())) != len(continuation):
        raise SirenityError("Siren pagination response properties must be unique")
    if "openapi_extra" in operation:
        raise SirenityError("Siren pagination owns openapi_extra")
    parameters = {
        query: f"$response.body#/{property_name.replace('~', '~0').replace('/', '~1')}"
        for query, property_name in continuation.items()
    }
    return route(
        path,
        response={status: response},
        operation_id=operation_id,
        openapi_extra={
            "responses": {
                status: {
                    "links": {
                        "next": {
                            "operationId": operation_id,
                            "parameters": parameters,
                        }
                    }
                }
            }
        },
        **operation,
    )


@dataclass(frozen=True)
class SirenMiddleware:
    """Install Siren through Django's standard middleware loader.

    The loader consumes an exact immutable ``SirenConfiguration`` or turns the current ``SIRENITY``
    mapping into one, then installs middleware from that same configuration. Resolved settings
    declarations remain fresh for each Django startup, autoreload process, and ``override_settings``
    lifecycle; a supplied configuration retains its caller-owned adapter lifecycle. ``OPENAPI`` and
    ``POLICY`` are dotted import paths; ``PROFILES`` is an optional sequence of profile paths. A
    missing policy retains the standard allow-all behavior.

    Sirenity derives an unambiguous immediate nested collection directly from Django Ninja's
    generated resource routes and response schemas. A parent response can expose canonical ``id``
    while its route uses a qualified placeholder such as ``example_group_id``; nested item responses
    expose their own ``id`` and retain ``example_group_id`` for the inherited parent segment. Create,
    read, and update responses need no ``openapi_extra`` declaration, ``x-sirenity`` metadata, policy
    relationship, or application-maintained operation mapping.

    Relationships that cannot be derived from route ownership can still use Django Ninja's native
    ``openapi_extra`` argument. Add the standard OpenAPI Link Object beneath the generated response,
    bind target path parameters from the response body, and declare the Siren relation and scope:

    ```python
    @api.get(
        "/api/example_groups/{example_group_id}",
        description="Read an example group.",
        operation_id="get_example_group",
        response=ExampleGroup,
        summary="Read example group",
        openapi_extra={
            "responses": {
                200: {
                    "links": {
                        "example_resources": {
                            "operationId": "list_example_group_resources",
                            "parameters": {
                                "path.example_group_id": "$response.body#/example_group_id",
                            },
                            "x-sirenity": {"rel": "collection", "scope": "collection"},
                        }
                    }
                }
            }
        },
    )
    def get_example_group(request, example_group_id: str):
        return {"example_group_id": example_group_id}
    ```

    Django Ninja merges this declaration into its generated response without an OpenAPI wrapper or
    post-processing provider. Middleware construction validates the operation target, path bindings,
    runtime expression, relation, and scope while compiling that generated document. The declared
    relationship therefore needs no application Siren policy solely to appear in the representation.
    """

    get_response: Callable[[object], object]
    middleware: SirenDjangoMiddleware = field(init=False)

    def __post_init__(self):
        try:
            from django.conf import settings

            configured = getattr(settings, "SIRENITY", None)
            if isinstance(configured, SirenConfiguration):
                selected = configured
            else:
                if not isinstance(configured, Mapping):
                    raise SirenityError("SIRENITY must be a SirenConfiguration or mapping")
                openapi = configured.get("OPENAPI")
                policy = configured.get("POLICY", "sirenity.SirenAllowAllPolicy")
                source_path = configured.get("SOURCE_PATH", "/")
                public_path = configured.get("PUBLIC_PATH", "/")
                profiles = configured.get("PROFILES", ())
                if not isinstance(openapi, str) or not openapi:
                    raise SirenityError("SIRENITY.OPENAPI must be a dotted import path")
                if not isinstance(policy, str) or not policy:
                    raise SirenityError("SIRENITY.POLICY must be a dotted import path")
                if not isinstance(source_path, str) or not isinstance(public_path, str):
                    raise SirenityError("SIRENITY source and public paths must be strings")
                if not isinstance(profiles, list | tuple) or any(
                    not isinstance(path, str) or not path for path in profiles
                ):
                    raise SirenityError("SIRENITY.PROFILES must be a sequence of dotted import paths")
                selected = siren_configuration(
                    openapi=openapi,
                    source_path=source_path,
                    public_path=public_path,
                    policy=policy,
                    profiles=tuple(profiles),
                )
            object.__setattr__(self, "middleware", selected.django(self.get_response))
        except Exception as error:
            raise SirenityError(f"Django Siren middleware startup failed: {error}") from error

    def __call__(self, request: object) -> object:
        return self.middleware(request)
