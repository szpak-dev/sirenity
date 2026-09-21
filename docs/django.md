# Django integration

## `SirenContinuation`

Declare one typed bounded Django Ninja or Ninja Extra continuation.

Wrap ``api.get`` or Ninja Extra's ``http_get``. The response model must expose a required
``has_more`` boolean and every mapped continuation property as a required non-nullable scalar.
Sirenity compiles the generated OpenAPI Link Object and returns one official ``next`` link plus
one typed MCP invocation only while ``has_more`` is true.

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

## `SirenMiddleware`

Install Siren through Django's standard middleware loader.

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

## `siren_follow_ups`

Declare typed read follow-ups for a Django Ninja or Ninja Extra operation.

Pass ``api.get`` for Django Ninja or ``http_get`` for Ninja Extra. Each mapping key becomes
the OpenAPI response-link name, while its :class:`SirenFollowUp` supplies the target operation,
response-property bindings, Siren relation, and target scope. Sirenity validates the generated
links during normal startup compilation and exposes authorized safe reads as typed MCP
invocations without parsing their rendered hrefs.

```python
from sirenity import SirenFollowUp, SirenScope, siren_follow_ups

@siren_follow_ups(
    api.get,
    "/api/dashboards/{dashboard_id}",
    response=Dashboard,
    operation_id="get_dashboard",
    follow_ups={
        "primary_record": SirenFollowUp(
            operation_id="get_record",
            parameters={"path.record_id": "primary_record_id"},
            rel="primary",
            scope=SirenScope.ENTITY,
        ),
    },
    summary="Read dashboard",
    description="Read one dashboard.",
)
def get_dashboard(request, dashboard_id: str) -> Dashboard:
    return Dashboard(dashboard_id=dashboard_id, primary_record_id="record-1")
```

Optional target arguments omitted from ``parameters`` remain absent from the typed invocation,
so defaults declared by the target operation continue to apply.

## `siren_pagination`

Declare one typed paginated Django Ninja or Ninja Extra operation.

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
