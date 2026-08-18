# sirenity

`sirenity` compiles a complete OpenAPI 3.1 document into a reusable Siren engine. At request
time, the engine turns application data and permissions into a Siren response with concrete links
and authorized actions.

Requires Python 3.12 or later.

## Install

```bash
python -m pip install sirenity
```

For local development, install `uv` and use the locked environment:

```bash
UV_CACHE_DIR=.dump/uv-cache uv sync --locked --all-groups
make verify
```

Version 2 is a breaking rewrite. See [MIGRATION.md](MIGRATION.md) when upgrading from version 1.

<!-- generated:public-api:start -->
## Usage

This section is generated from the docstrings of the supported root imports. Run `make docs` after changing a public API example or its guidance.

### `siren_adapter`

Compile a framework-neutral boundary for operation-aware Siren HTTP responses.

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

### `siren`

Compile a complete OpenAPI 3.1 document into a reusable Siren engine.

Call this once during application startup, then call `engine.project(context)` for each
negotiated Siren response. OpenAPI defines links, methods, and candidate fields; the context's
capabilities decide which candidate actions are present in that response.

#### Example

```python
from sirenity import SirenContext, siren

openapi = {
    "openapi": "3.1.1",
    "info": {"title": "Records API", "version": "1.0"},
    "paths": {
        "/records": {"get": {"operationId": "list_records", "responses": {"200": {"description": "OK"}}}},
        "/records/{record_id}": {
            "parameters": [{"name": "record_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {"operationId": "get_record", "responses": {"200": {"description": "OK"}}},
            "patch": {
                "operationId": "rename_record",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["metadata"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "metadata": {
                                        "type": "object",
                                        "properties": {"source": {"type": "string"}},
                                    },
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
}

engine = siren(openapi)
document = engine.project(
    SirenContext(
        base_url="https://api.example.com",
        resource="record",
        value={"id": "42", "title": "Architecture"},
        capabilities=frozenset({"get_record", "rename_record"}),
    )
)

payload = document.model_dump(by_alias=True, mode="json", exclude_none=True)

assert payload["actions"][0] == {
    "name": "get_record",
    "href": "https://api.example.com/records/42",
    "method": "GET",
}
```

#### OpenAPI requirements

The final plural static segment of a route is a collection; adding one path parameter forms
its entity route. Prefixes and nested collections are supported. Every non-root HTTP operation
needs a unique `operationId`. Local `#/components/parameters`, `#/components/requestBodies`,
and `#/components/schemas` references are resolved; external and path-item references are not.

#### Action field support matrix

Path parameters substitute into action URLs and never become fields. Query parameters and
properties of an `application/json` object body become fields:

| OpenAPI schema | Siren field type |
| --- | --- |
| `string`, including `uuid` | `text` |
| formatted `string` | matching Siren field type |
| `integer` or `number` | `number` |
| `boolean` | `checkbox` |
| non-enum array or repeated query parameter | delegated `/array/v1`; no synthetic field |
| scalar `enum` | `radio` with selectable values |
| flat array with an item `enum` | `checkbox` with selectable values |
| object with concrete properties or a typed map | delegated `/object/v1`; no synthetic field |
| schema-less open object | delegated `/json/v1`; no synthetic field |
| header or cookie parameter | delegated; no synthetic field |
| one non-JSON request media type | delegated action with that media type |

`email`, `uri`, `date`, `date-time`, and `time` map to `email`, `url`, `date`,
`datetime-local`, and `time`, respectively.

Required and nullable controls compile as ordinary standard Siren fields: validation remains
server-enforced because official Siren has no `required` or `nullable` members. Arrays without
item enum values retain their complete schema in the structured-form extension; the OpenAPI
serialization contract remains authoritative for submission. `allOf` scalar fragments and a
`oneOf` or `anyOf` containing one scalar plus
`null` are accepted when they normalize unambiguously.

An object without concrete properties is open when `additionalProperties` is omitted, `true`,
or `{}` and retains its complete schema in a `/json/v1` control. Named object properties take
precedence and use `/object/v1`; typed maps also remain object controls.

Structured values, header and cookie parameters, and one non-JSON request body are delegated
to the API contract and client transport; official Siren has no standard members for their
paths, serialization, or placement. Multiple non-JSON media types, ambiguous compositions,
unsupported string formats, and `HEAD`, `OPTIONS`, or `TRACE` operations are rejected during
this startup call.

#### Adapter-facing operation inputs

Use `engine.operation_input(operation_id)` when an adapter needs the compiled request contract.
It returns the selected media type, the fully resolved request-body `definition`, the names in
`official_fields`, and separate `delegated_inputs` for structured query values, headers,
cookies, and bodies. Each delegated input retains its location, required state, media type,
normalized parameter serialization controls, and resolved definition, so an adapter does not
need to parse OpenAPI again.

```python
operation_input = engine.operation_input("rename_record")

payload = {"title": "New title"}
if operation_input is not None:
    metadata = next(value for value in operation_input.delegated_inputs if value.name == "metadata")
    if metadata.location == "body" and metadata.required:
        payload[metadata.name] = {"source": "browser"}

transport.request("PATCH", "/records/42", json=payload)
```

This metadata is separate from projection. `engine.project(context)` continues to produce an
extension-free Siren document containing only official fields.

Call `audit(openapi)` first when a consumer needs a deterministic list of every current
incompatibility before using this strict fail-fast entry point.

#### Response relationships

A response `links` object can declare a navigational Siren relationship. Target an operation with
standard `operationId` or local `operationRef`, bind each target path parameter with a
`$response.body#...` runtime expression, and add `x-sirenity` metadata for the Siren relation and
target scope. The compiler rejects an unknown target, an incomplete path binding, or malformed
expression during startup; a missing runtime response value fails projection deterministically.

```yaml
responses:
  "200":
    links:
      diagrams:
        operationId: list_diagram_set_diagrams
        parameters:
          path.diagram_set_id: $response.body#/diagram_set_id
        x-sirenity:
          rel: collection
          scope: collection
```

Declared relationships do not need application capability policy merely to appear. Continue using
`SirenRelationship` for relationships that are defined by application runtime policy rather than
the OpenAPI contract.

#### Explicit title metadata

The root document uses `info.title`, and exposes `info.version` as the official Siren
`properties.version` value. An operation's `summary` becomes its action title. Resource titles
come only from explicitly connected successful response schemas: an object schema on the exact
entity route names an entity, while an array schema on the exact collection route names its
collection and its item schema names embedded items and entities. A meaningful array title names
the collection; framework-generated `Response` wrapper titles and item DTO titles do not replace
the resource title for collection navigation. Self and root collection links reuse those compiled
titles.

```yaml
info:
  title: Example Service
  version: 4.0.0
paths:
  /articles/{article_id}:
    get:
      operationId: get_article
      summary: Read article
      responses:
        "200":
          description: Article
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Article"
components:
  schemas:
    Article:
      type: object
      title: Article
```

`SirenContext.title`, `SirenResponseContext.title`, and `SirenRelationship.title` override the
relevant compiled default. For collections, `item_titles` supplies one runtime title per item.
Without explicit item titles, a non-empty string `title` property, then a non-empty string `name`
property, supplies the item and self-link title before the compiled resource title. Missing titles
remain absent: the engine does not humanize operation IDs, guess labels from URLs, strip DTO
suffixes, or apply language-specific inflection. Collection title precedence is an explicit runtime
title, a meaningful array-schema title, then the resource title. When operations declare different
schema titles, the exact GET representation takes precedence, followed by other operations in
OpenAPI declaration order.

#### Framework integration is one startup call

Give the framework-generated document directly to `siren()` after routes are registered:

```python
engine = siren(app.openapi())  # FastAPI
engine = siren(api.get_openapi_schema())  # Django Ninja / Django Ninja Extra
```

#### HTTP response contract

`engine.project(context)` returns a `SirenDocument`, not a dictionary. Serialize it with
`document.model_dump(by_alias=True, mode="json", exclude_none=True)` and send that payload as
`application/vnd.siren+json`. The document contains only official Siren members; action fields
never include the non-standard `required` member.

#### Operation-aware response projection

When an adapter knows the executed operation and HTTP status, pass a `SirenResponseContext`
to `engine.project_response(...)`. The engine selects the compiled response status, media
type, and resolved schema. Arrays become collection documents, objects returned from an
entity's exact route become entity documents, content-free responses become `empty` documents,
and statuses from 400 onward become `error` documents whose properties preserve the status and
structured result.

```python
from sirenity import SirenResponseContext

document = engine.project_response(SirenResponseContext(
    operation_id="get_record",
    status=200,
    result={"record_id": "42", "title": "Architecture"},
    base_url="https://api.example.com",
))
```

An object response on the exact API root becomes the entry point, an object on an exact resource
collection or entity route becomes an entity, and an object on a subcommand route becomes a
command result. Set response-context `representation` to override an exceptional operation. No
identifier property name is inferred; compiled route parameters and explicit path values resolve
entity links.

Set `source_path` to the OpenAPI route prefix and `public_path` to the independently
mounted Siren prefix. Both prefixes are segment-aware and normalized without a trailing
slash. Every OpenAPI path must belong to `source_path`.

### `audit`

Inspect a valid OpenAPI document against the current official-Siren support boundary.

Call this during startup before `siren(openapi)` when a consumer needs every currently
unsupported construct at once. The report exposes typed findings and `render()` for terminal
or CI output; `siren(openapi)` remains the strict fail-fast compilation entry point.

### `SirenStructuredFormProfile`

Emit the versioned Modwire structured-form extension for delegated inputs.

This opt-in profile adds the non-standard action member
`https://modwire.dev/siren/structured-form/v1`. Its value has `version: "1"` and ordered
`controls`. Each control exposes `name`, `location`, `required`, a resolved OpenAPI `schema`, and
one versioned control URI. Body controls include `mediaType`; query, header, and cookie controls
instead include materialized `style`, `explode`, and `allowReserved` serialization.

Object and array controls use the `/object/v1` and `/array/v1` control URIs. Open JSON objects
use `/json/v1`. Only delegated inputs are emitted, so ordinary official Siren fields are never
duplicated. The profile walks actions recursively through embedded representations.

### `SirenScope`

Enum where members are also (and must be) strings

### `SirenResponseContext`

Supply an executed OpenAPI operation and result for operation-aware projection.

The compiled response status, media type, and schema determine whether the result is empty,
an object, or an array. Array responses project as collections and object responses from an
entity's or collection's exact route project as entities, an exact root operation projects as
the API entry point, and other object responses project as command results. Set `representation`
to override an exceptional operation. Root projection preserves executed mapping properties while
compiled OpenAPI version metadata wins a `version` collision. `title` overrides the compiled
resource or operation title. For an array response, `item_titles` supplies one explicit title per
result item.

### `SirenRelationship`

Describe a runtime relationship to another OpenAPI resource.

A relationship targets either an entity or a collection through its required `scope`. Set
`embedded` only for an entity relationship when related values should be included as a Siren
embedded representation instead. `title` overrides the compiled title for this link or
embedded representation.

Use `path_values` to select and render a nested collection route. Capabilities must belong to
the relationship's selected scope.

```python
from sirenity import SirenRelationship, SirenScope

relationship = SirenRelationship(
    rel=("collection",),
    resource="diagram",
    scope=SirenScope.COLLECTION,
    path_values={"diagram_set_id": diagram_set_id},
    capabilities=frozenset({"list_diagram_set_diagrams"}),
)
```

### `SirenOperationInput`

Expose normalized input metadata for one compiled OpenAPI operation.

`official_fields` names the values emitted as standard Siren action fields.
`delegated_inputs` retains structured query values, headers, cookies, and body values for an
adapter or transport. `definition` is the normalized request-body schema when one is declared.

### `SirenMiddleware`

Install Siren through Django's standard middleware loader.

Add the root import directly to Django settings. The OpenAPI target may be a mapping, a callable
returning one, or a Django Ninja/Ninja Extra API exposing `get_openapi_schema()`. By default the
middleware exposes every capability owned by the matched operation's compiled graph scope. An
optional policy target may restrict those capabilities or override exceptional response semantics.
Optional `PROFILES` dotted paths are instantiated once with the adapter.

```python
# example_project/api.py
from ninja_extra import ControllerBase, NinjaExtraAPI, api_controller, http_get
api = NinjaExtraAPI()

@api_controller("/articles")
class ArticleController(ControllerBase):
    @http_get("/{article_id}", operation_id="get_article")
    def get_article(self, article_id: str) -> dict[str, str]:
        return {"article_id": article_id, "title": "One-line Siren"}

api.register_controllers(ArticleController)

def siren_openapi():
    return api.get_openapi_schema(path_prefix="/api")

# settings.py
MIDDLEWARE = [
    "django.middleware.http.ConditionalGetMiddleware",
    "sirenity.SirenMiddleware",
]
MODWIRE_SIREN = {
    "OPENAPI": "example_project.api.siren_openapi",
    "SOURCE_PATH": "/api",
    "PUBLIC_PATH": "/siren",
    "PROFILES": ["sirenity.SirenStructuredFormProfile"],
}

# urls.py
from django.urls import path
from example_project.api import api
urlpatterns = [path("api/", api.urls)]
```

Django constructs this class with only `get_response`. Each middleware instance resolves the current
settings and compiles after importing the configured API, once, so autoreload processes and overridden
test settings receive a fresh completed route catalogue without process-global adapter state. Invalid or
premature configuration raises `ModwireSirenError` during middleware startup.

### `SirenLink`

Describe a navigational Siren link.

### `SirenFieldValue`

Describe a selectable Siren action field value.

### `SirenField`

Describe an official Siren action field.

### `SirenEmbeddedRepresentation`

Represent a Siren sub-entity embedded in full.

### `SirenEmbeddedLink`

Represent a Siren sub-entity linked by URI.

### `SirenDocument`

Represent an official Siren entity document.

Project an engine request into this immutable public value, then serialize it with
`model_dump(by_alias=True, mode="json", exclude_none=True)` for an
`application/vnd.siren+json` response. Navigation belongs in `links`; embedded sub-entities
belong in `entities`.

### `SirenDjangoMiddleware`

Render negotiated Django Ninja/Ninja Extra JSON responses as Siren.

Configure this callable as Django middleware. The standard loader supplies
`SirenAllowAllPolicy` when no application authorization policy is configured; direct callers
provide a `SirenCapabilityPolicy` or a callable returning `SirenAdapterPolicy`.
It calls the wrapped operation exactly once and transforms only matched JSON-compatible or
content-free responses. Unmatched, non-JSON, streaming, redirect, 304, and already-Siren responses
pass through without projection, as do all requests that do not select Siren. Negotiation honors
quality, specificity, wildcards, and case-insensitive media types; missing or wildcard-only Accept
values retain JSON because neither explicitly prefers Siren. Negotiable JSON, Siren, and 304
responses vary on Accept even when the original response object is returned.
Unmatched errors also pass through: the bridge does not infer API ownership from URL prefixes.

Transformed responses retain cookies and semantic or security headers, and discard validators,
digests, encodings, ranges, and framing tied to the source JSON bytes. Place Django's
ConditionalGetMiddleware before this middleware so it evaluates the final Siren representation on
the response path; a downstream 304 remains untouched because its representation body is unavailable.

When source and public paths differ, the middleware maps a matched public route to its compiled
source route before Django dispatch and restores the public request path before projection.

### `SirenDelegatedInput`

Describe a normalized OpenAPI input delegated to an adapter or transport.

`kind` is the compiler-normalized structured control shape. Parameter serialization defaults
are materialized in `style`, `explode`, and `allow_reserved`; body inputs instead carry their
selected `media_type`.

### `SirenContext`

Supply runtime state used to project a Siren document.

Use the default `"entity"` scope for one resource, `"collection"` for a list, and `"root"`
for an API entry point. A resource is required outside root scope and is the singular name
derived from the collection route: `"record"` for `/records`. If the same resource appears
in multiple nested routes, `path_values` selects the route with matching parent parameters.

| Field | Purpose |
| --- | --- |
| `base_url` | Public origin joined with OpenAPI paths. |
| `scope` | `"root"`, `"collection"`, or `"entity"`. |
| `resource` | Derived singular resource name; required outside root. |
| `title` | Explicit document title overriding compiled OpenAPI metadata. |
| `value` | Entity or root properties and entity path parameters. |
| `items` | Entity mappings for a collection. |
| `item_titles` | Optional explicit titles aligned with collection items. |
| `item_capabilities` | Optional permitted operation IDs for each collection item. |
| `relationships` | Linked or embedded related resources for this document. |
| `path_values` | Missing path parameters, such as a parent resource ID or a root command target. |
| `query` | Ordered query pairs for self and action links. |
| `capabilities` | Permitted OpenAPI `operationId` values. |

### `SirenCompatibilityReport`

Expose deterministic OpenAPI-to-Siren compatibility findings.

### `SirenCompatibilityFinding`

Describe one OpenAPI construct outside the current official-Siren boundary.

### `SirenCapabilityPolicy`

Select application authorization and optional projection overrides for one response.

### `SirenAllowAllPolicy`

Permit every capability owned by the matched operation's compiled graph scope.

### `SirenAdapterResponse`

Represent an HTTP-ready official Siren response without framework dependencies.

### `SirenAdapterRequest`

Describe one already-executed HTTP operation for Siren projection.

Pass the framework's executed `operation_id` when it is available. Otherwise provide `method`
and `path` so the adapter can resolve the operation from its startup-compiled route catalogue.
`result` is the already-produced application value: the adapter never redispatches the operation.

### `SirenAdapterProfile`

Extend a fresh adapter document using public normalized operation metadata.

The adapter supplies the matched operation and input, a catalogue for every action operation, the
projected response context, and a newly serialized document. Input values are deep copies, so a
custom profile cannot mutate the cached engine graph. Return a JSON mapping for the next profile in
the ordered pipeline; extension members are the profile's explicit non-standard contract.

### `SirenAdapterPolicy`

Declare application-owned authorization and optional projection overrides.

Adapters never infer permissions from OpenAPI or result identifiers. Representation defaults come
from the compiled API graph and may be overridden for exceptional operations. For a collection
response, `item_titles` supplies one explicit title per result item in the same order as
`item_capabilities`.

### `SirenAdapterMatch`

!!! abstract "Usage Documentation"
    [Models](../concepts/models.md)

A base class for creating Pydantic models.

Attributes:
    __class_vars__: The names of the class variables defined on the model.
    __private_attributes__: Metadata about the private attributes of the model.
    __signature__: The synthesized `__init__` [`Signature`][inspect.Signature] of the model.

    __pydantic_complete__: Whether model building is completed, or if there are still undefined fields.
    __pydantic_core_schema__: The core schema of the model.
    __pydantic_custom_init__: Whether the model has a custom `__init__` function.
    __pydantic_decorators__: Metadata containing the decorators defined on the model.
        This replaces `Model.__validators__` and `Model.__root_validators__` from Pydantic V1.
    __pydantic_generic_metadata__: A dictionary containing metadata about generic Pydantic models.
        The `origin` and `args` items map to the [`__origin__`][genericalias.__origin__]
        and [`__args__`][genericalias.__args__] attributes of [generic aliases][types-genericalias],
        and the `parameter` item maps to the `__parameter__` attribute of generic classes.
    __pydantic_parent_namespace__: Parent namespace of the model, used for automatic rebuilding of models.
    __pydantic_post_init__: The name of the post-init method for the model, if defined.
    __pydantic_root_model__: Whether the model is a [`RootModel`][pydantic.root_model.RootModel].
    __pydantic_serializer__: The `pydantic-core` `SchemaSerializer` used to dump instances of the model.
    __pydantic_validator__: The `pydantic-core` `SchemaValidator` used to validate instances of the model.

    __pydantic_fields__: A dictionary of field names and their corresponding [`FieldInfo`][pydantic.fields.FieldInfo] objects.
    __pydantic_computed_fields__: A dictionary of computed field names and their corresponding [`ComputedFieldInfo`][pydantic.fields.ComputedFieldInfo] objects.

    __pydantic_extra__: A dictionary containing extra values, if [`extra`][pydantic.config.ConfigDict.extra]
        is set to `'allow'`.
    __pydantic_fields_set__: The names of fields explicitly set during instantiation.
    __pydantic_private__: Values of private attributes set on the model instance.

### `SirenAdapter`

Project already-executed framework results through a startup-compiled Siren engine.

Use `match()` when a framework exposes only its HTTP method and path. Use `respond()` after the
application operation has executed exactly once. The adapter preserves semantic response headers
while removing validators and content metadata tied to the source bytes, then returns an HTTP-ready
payload with the official Siren media type.

Route resolution compares exact segment counts and ranks matching templates position by position,
with literal segments ahead of parameters. Source and public templates use the same ranking. Adapter
construction rejects same-method templates that become identical after parameter names are removed.
Explicit profiles form a validated ordered pipeline over fresh serialized payloads and deep-copied
public operation-input values; the cached engine graph remains immutable across requests.

### `SirenAction`

Describe an available Siren action.

### `ModwireSirenError`

Indicate a Modwire Siren operation failure.

## Public API

The supported root imports below are generated from `sirenity.__all__`.

| Symbol | Purpose | Primary API |
| --- | --- | --- |
| `ModwireSirenError` | Indicate a Modwire Siren operation failure. | — |
| `SirenAction` | Describe an available Siren action. | — |
| `SirenAdapter` | Project already-executed framework results through a startup-compiled Siren engine. | `match(method: <class 'str'>, path: <class 'str'>) -> sirenity.contexts.runtime.adapter.values.match.SirenAdapterMatch | None`<br>`dispatch_path(method: <class 'str'>, path: <class 'str'>) -> str | None`<br>`render_path(template: <class 'str'>, values: collections.abc.Mapping[str, JsonValue]) -> <class 'str'>`<br>`respond(request: <class 'sirenity.contexts.runtime.adapter.values.request.SirenAdapterRequest'>) -> <class 'sirenity.contexts.runtime.adapter.values.response.SirenAdapterResponse'>`<br>`capabilities(operation_id: <class 'str'>) -> frozenset[str]`<br>`error(request: <class 'sirenity.contexts.runtime.adapter.values.request.SirenAdapterRequest'>) -> <class 'sirenity.contexts.runtime.document.values.document.SirenDocument'>` |
| `SirenAdapterMatch` | !!! abstract "Usage Documentation" | — |
| `SirenAdapterPolicy` | Declare application-owned authorization and optional projection overrides. | — |
| `SirenAdapterProfile` | Extend a fresh adapter document using public normalized operation metadata. | `apply(operation_id: <class 'str'>, operation_input: sirenity.contexts.runtime.operation_input.values.operation.SirenOperationInput | None, operation_inputs: collections.abc.Mapping[str, sirenity.contexts.runtime.operation_input.values.operation.SirenOperationInput | None], document: collections.abc.Mapping[str, JsonValue], context: <class 'sirenity.contexts.runtime.request.values.response.SirenResponseContext'>) -> collections.abc.Mapping[str, JsonValue]` |
| `SirenAdapterRequest` | Describe one already-executed HTTP operation for Siren projection. | — |
| `SirenAdapterResponse` | Represent an HTTP-ready official Siren response without framework dependencies. | — |
| `SirenAllowAllPolicy` | Permit every capability owned by the matched operation's compiled graph scope. | `select(operation_id: str | None, status: <class 'int'>, request: <class 'object'>, result: JsonValue) -> <class 'sirenity.contexts.runtime.adapter.values.policy.SirenAdapterPolicy'>` |
| `SirenCapabilityPolicy` | Select application authorization and optional projection overrides for one response. | `select(operation_id: str | None, status: <class 'int'>, request: <class 'object'>, result: JsonValue) -> <class 'sirenity.contexts.runtime.adapter.values.policy.SirenAdapterPolicy'>` |
| `SirenCompatibilityFinding` | Describe one OpenAPI construct outside the current official-Siren boundary. | — |
| `SirenCompatibilityReport` | Expose deterministic OpenAPI-to-Siren compatibility findings. | `compatible: <class 'bool'>`<br>`render() -> <class 'str'>` |
| `SirenContext` | Supply runtime state used to project a Siren document. | — |
| `SirenDelegatedInput` | Describe a normalized OpenAPI input delegated to an adapter or transport. | — |
| `SirenDjangoMiddleware` | Render negotiated Django Ninja/Ninja Extra JSON responses as Siren. | — |
| `SirenDocument` | Represent an official Siren entity document. | — |
| `SirenEmbeddedLink` | Represent a Siren sub-entity linked by URI. | — |
| `SirenEmbeddedRepresentation` | Represent a Siren sub-entity embedded in full. | — |
| `SirenField` | Describe an official Siren action field. | — |
| `SirenFieldValue` | Describe a selectable Siren action field value. | — |
| `SirenLink` | Describe a navigational Siren link. | — |
| `SirenMiddleware` | Install Siren through Django's standard middleware loader. | — |
| `SirenOperationInput` | Expose normalized input metadata for one compiled OpenAPI operation. | — |
| `SirenRelationship` | Describe a runtime relationship to another OpenAPI resource. | — |
| `SirenResponseContext` | Supply an executed OpenAPI operation and result for operation-aware projection. | — |
| `SirenScope` | Enum where members are also (and must be) strings | — |
| `SirenStructuredFormProfile` | Emit the versioned Modwire structured-form extension for delegated inputs. | `apply(operation_id: <class 'str'>, operation_input: sirenity.contexts.runtime.operation_input.values.operation.SirenOperationInput | None, operation_inputs: collections.abc.Mapping[str, sirenity.contexts.runtime.operation_input.values.operation.SirenOperationInput | None], document: collections.abc.Mapping[str, JsonValue], context: <class 'sirenity.contexts.runtime.request.values.response.SirenResponseContext'>) -> collections.abc.Mapping[str, JsonValue]`<br>`enrich(entity: collections.abc.Mapping[str, JsonValue], operation_inputs: collections.abc.Mapping[str, sirenity.contexts.runtime.operation_input.values.operation.SirenOperationInput | None]) -> collections.abc.Mapping[str, JsonValue]`<br>`control(delegated: <class 'sirenity.contexts.runtime.operation_input.values.delegated.SirenDelegatedInput'>) -> collections.abc.Mapping[str, JsonValue]` |
| `audit` | Inspect a valid OpenAPI document against the current official-Siren support boundary. | — |
| `siren` | Compile a complete OpenAPI 3.1 document into a reusable Siren engine. | — |
| `siren_adapter` | Compile a framework-neutral boundary for operation-aware Siren HTTP responses. | — |
<!-- generated:public-api:end -->
