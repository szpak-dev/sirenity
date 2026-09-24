"""Django integration.

<!-- docs:order=40 -->
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import NotRequired, TypedDict

from ..contexts.runtime.adapter import SirenDjangoMiddleware
from ..contexts.runtime.mcp import SirenMcpToolCatalogueService
from ..wiring import application
from .configuration import SirenConfiguration, SirenConfigurationResolver
from .follow_up import SirenOperationDecorator, SirenRouteDecorator
from .item_follow_up import SirenItemFollowUp
from .source_input import SirenSourceInput


class SirenDjangoSettings(TypedDict):
    OPENAPI: str
    SOURCE_PATH: NotRequired[str]
    PUBLIC_PATH: NotRequired[str]
    POLICY: NotRequired[str]
    PROFILES: NotRequired[list[str]]


@dataclass(frozen=True)
class SirenContinuation[**P, R, S]:
    """Declare one typed bounded Django Ninja or Ninja Extra continuation.

    Wrap ``api.get`` or Ninja Extra's ``http_get``. The response model must expose a required
    ``has_more`` boolean and every mapped continuation property as a required non-nullable scalar.
    Sirenity compiles the generated OpenAPI Link Object and returns one official ``next`` link plus
    one typed MCP invocation only while ``has_more`` is true.
    ``source_inputs`` explicitly retains required, non-null source path, query, or body inputs; all
    remaining source inputs are excluded from the continuation.

    ```python
    from ninja import Schema

    from sirenity import SirenContinuation

    class ExampleJobState(Schema):
        example_job_id: str
        has_more: bool
        next_cursor: str

    @SirenContinuation(
        api.get,
        "/api/example-jobs/{example_job_id}",
        response=ExampleJobState,
        operation_id="get_example_job",
        continuation={"cursor": "next_cursor"},
        summary="Read example job",
        description="Read the current example job state.",
    )
    def get_example_job(request, example_job_id: str, cursor: str = "first") -> ExampleJobState:
        return ExampleJobState(
            example_job_id=example_job_id,
            has_more=False,
            next_cursor=cursor,
        )
    ```
    """

    route: SirenRouteDecorator[P, R, S]
    path: str
    response: type[S]
    operation_id: str
    continuation: Mapping[str, str]
    summary: str
    description: str
    status: int = 200
    source_inputs: Mapping[str, SirenSourceInput] = field(default_factory=dict)

    def __call__(self, handler: Callable[P, R]) -> Callable[P, R]:
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
                                "x-sirenity": {
                                    "continuation": "bounded",
                                    **(
                                        {
                                            "sourceInputs": {
                                                target: (
                                                    "$request.body#/"
                                                    + source.name.replace("~", "~0").replace("/", "~1")
                                                    if source.location == "body"
                                                    else f"$request.{source.location}.{source.name}"
                                                )
                                                for target, source in self.source_inputs.items()
                                            }
                                        }
                                        if self.source_inputs
                                        else {}
                                    ),
                                },
                            }
                        }
                    }
                }
            },
        )
        return decorator(handler)


def siren_pagination[**P, R, S](
    route: SirenRouteDecorator[P, R, S],
    path: str,
    *,
    response: type[S],
    operation_id: str,
    continuation: Mapping[str, str],
    summary: str,
    description: str,
    source_inputs: Mapping[str, SirenSourceInput],
    item_follow_ups: Mapping[str, SirenItemFollowUp],
    status: int,
) -> SirenOperationDecorator[P, R]:
    """Declare one typed paginated Django Ninja or Ninja Extra operation.

    Pass ``api.get`` for Django Ninja or ``http_get`` for Ninja Extra. The response model and
    continuation mapping produce one successful response containing a standard OpenAPI ``next``
    Link Object. The operation ID is declared once and reused as the link target. Sirenity's normal
    startup compilation validates every mapped query parameter and response property.
    ``source_inputs`` explicitly retains required, non-null source path, query, or body inputs; all
    remaining source inputs are excluded from the next-page invocation.
    ``item_follow_ups`` declares safe navigation relative to every item in the page collection.

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
        source_inputs={},
        item_follow_ups={},
        status=200,
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
        summary=summary,
        description=description,
        openapi_extra={
            "responses": {
                status: {
                    "links": {
                        "next": {
                            "operationId": operation_id,
                            "parameters": parameters,
                            **(
                                {
                                    "x-sirenity": {
                                        "sourceInputs": {
                                            target: (
                                                "$request.body#/" + source.name.replace("~", "~0").replace("/", "~1")
                                                if source.location == "body"
                                                else f"$request.{source.location}.{source.name}"
                                            )
                                            for target, source in source_inputs.items()
                                        }
                                    }
                                }
                                if source_inputs
                                else {}
                            ),
                        },
                        **{
                            name: {
                                "operationId": follow_up.operation_id,
                                "parameters": {
                                    argument: ("$response.body#/" + property_name.replace("~", "~0").replace("/", "~1"))
                                    for argument, property_name in follow_up.parameters.items()
                                },
                                "x-sirenity": {
                                    "rel": follow_up.rel,
                                    "scope": follow_up.scope.value,
                                    "itemCollection": (
                                        "$response.body#/"
                                        + follow_up.item_collection.replace("~", "~0").replace("/", "~1")
                                    ),
                                    **(
                                        {
                                            "sourceInputs": {
                                                target: (
                                                    "$request.body#/"
                                                    + source.name.replace("~", "~0").replace("/", "~1")
                                                    if source.location == "body"
                                                    else f"$request.{source.location}.{source.name}"
                                                )
                                                for target, source in follow_up.source_inputs.items()
                                            }
                                        }
                                        if follow_up.source_inputs
                                        else {}
                                    ),
                                },
                            }
                            for name, follow_up in item_follow_ups.items()
                        },
                    }
                }
            }
        },
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

    Use :func:`siren_follow_ups` when a successful read advertises independent safe reads. It creates
    standard OpenAPI Link Objects from target operation identifiers and response-property bindings;
    Sirenity validates them and exposes authorized executable targets through MCP ``follow_ups``.
    Other relationships that cannot be derived from route ownership can still use Django Ninja's
    native ``openapi_extra`` argument. Add the Link Object beneath the generated response, bind target
    path parameters from the response body, and declare the Siren relation and scope:

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

        configured: SirenConfiguration | SirenDjangoSettings = settings.SIRENITY
        match configured:
            case SirenConfiguration():
                selected = configured
            case declaration:
                resolver = SirenConfigurationResolver(
                    catalogue_service=application.container.get(SirenMcpToolCatalogueService)
                )
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
