"""Django integration.

<!-- docs:order=40 -->
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import NotRequired, Protocol, TypedDict

from pydantic import JsonValue

from ..contexts.runtime.adapter import SirenDjangoMiddleware
from ..contexts.runtime.mcp import SirenMcpToolCatalogueService
from ..wiring import application
from .configuration import SirenConfigurationResolver


class SirenHandler[**P, R](Protocol):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


class SirenOperationDecorator[**P, R](Protocol):
    def __call__(self, handler: SirenHandler[P, R]) -> SirenHandler[P, R]: ...


class SirenRouteDecorator[**P, R, S](Protocol):
    def __call__(
        self,
        path: str,
        *,
        response: Mapping[int, type[S]],
        operation_id: str,
        openapi_extra: Mapping[str, JsonValue],
        **operation: object,
    ) -> SirenOperationDecorator[P, R]: ...


class SirenDjangoSettings(TypedDict):
    OPENAPI: str
    SOURCE_PATH: NotRequired[str]
    PUBLIC_PATH: NotRequired[str]
    POLICY: NotRequired[str]
    PROFILES: NotRequired[list[str]]


@dataclass(frozen=True)
class SirenContinuation[**P, R, S]:
    route: SirenRouteDecorator[P, R, S]
    path: str
    response: type[S]
    operation_id: str
    continuation: Mapping[str, str]
    summary: str
    description: str
    status: int = 200

    def __call__(self, handler: SirenHandler[P, R]) -> SirenHandler[P, R]:
        parameters = {
            name: f"$response.body#/{property_name.replace('~', '~0').replace('/', '~1')}"
            for name, property_name in self.continuation.items()
        }
        decorator = self.route(
            self.path,
            response={self.status: self.response},
            operation_id=self.operation_id,
            summary=self.summary,
            description=self.description,
            openapi_extra={
                "responses": {
                    self.status: {
                        "links": {
                            "next": {
                                "operationId": self.operation_id,
                                "parameters": parameters,
                                "x-sirenity": {"continuation": "bounded"},
                            }
                        }
                    }
                }
            },
        )
        return decorator(handler)


def siren_pagination[**P, R, S](
    route: SirenRouteDecorator[P, R, S],
    path: str = "",
    *,
    response: type[S],
    operation_id: str,
    continuation: Mapping[str, str],
    status: int = 200,
    **operation: object,
) -> SirenOperationDecorator[P, R]:
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

    The loader turns the current ``SIRENITY`` mapping into one immutable configuration, then installs
    middleware from that configuration. Resolved settings declarations remain fresh for each Django
    startup, autoreload process, and ``override_settings`` lifecycle. ``OPENAPI`` and ``POLICY`` are
    dotted import paths; ``PROFILES`` is an optional sequence of profile paths. A missing policy retains
    the standard allow-all behavior.

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
        from django.conf import settings

        declaration: SirenDjangoSettings = settings.SIRENITY
        resolver = SirenConfigurationResolver(catalogue_service=application.container.get(SirenMcpToolCatalogueService))
        selected = resolver.provider(
            declaration["OPENAPI"],
            declaration.get("SOURCE_PATH", "/"),
            declaration.get("PUBLIC_PATH", "/"),
            declaration.get("POLICY", "sirenity.SirenAllowAllPolicy"),
            tuple(declaration.get("PROFILES", ())),
        )
        object.__setattr__(self, "middleware", selected.django(self.get_response))

    def __call__(self, request: object) -> object:
        return self.middleware(request)
