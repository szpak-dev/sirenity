# Migration to 2.0.0

Version 2.0.0 replaces the version 1 projection library with a small OpenAPI-to-Siren engine. This
is a breaking release; version 1 imports, decorators, resource extensions, profiles, client, and
framework integrations no longer exist.

## What changed

Version 1 required applications to declare `x-siren-resource` metadata, register resource specs,
create Siren controllers, and project every entity or collection manually.

Version 2 treats OpenAPI as the structural contract. It derives resources from canonical paths,
compiles one immutable `SirenApi`, and projects a `SirenContext` at runtime.

```python
from sirenity import SirenContext, siren

engine = siren(openapi)
document = engine.project(
    SirenContext(
        base_url="https://api.example.com",
        resource="record",
        value={"id": "42", "title": "Architecture"},
        capabilities=frozenset({"get_record", "rename_record"}),
    )
)

response_body = document.model_dump(by_alias=True, mode="json", exclude_none=True)
# Send response_body as application/vnd.siren+json.
```

`engine.project()` now returns the immutable public `SirenDocument`, not a dictionary. It emits
only official Siren members: navigational transitions are `links`; related sub-entities are
`entities`; action fields never include the non-standard `required` member.

## Removed APIs

Remove all use of these version 1 APIs:

- the legacy facade and factory
- `SirenEntityRequest`, `SirenCollectionRequest`, and resource specs
- `x-siren-resource` injection and validation
- `siren_entity`, `siren_collection`, and `siren_resource`
- Ninja Extra and Django integrations
- UI profile support
- `SirenClient`

## OpenAPI requirements

Version 2 derives resources from conventional OpenAPI route segments. A collection ends in a
plural static segment; its entity route adds one path parameter. Prefixes, nested collections,
and arbitrary parameter names are supported:

```text
/api/v1/records
/accounts/{account}/records
/accounts/{account}/records/{record}
```

The resource name is derived from the final collection segment. Operations require unique
`operationId` values. Exact routes and static subpaths belong to their matching collection or
entity; a nested resource owns the longest matching route. Unsupported or ambiguous routes fail
at startup rather than silently omitting an operation.

```yaml
paths:
  /records:
    get:
      operationId: list_records
  /records/{record}:
    get:
      operationId: get_record
    patch:
      operationId: rename_record
```

## HTTP framework integration

The package no longer owns a Django or Ninja adapter. Keep your existing controller routes. At
application setup, pass Ninja's generated OpenAPI document to `siren()`. At response time, build a
`SirenContext` from the request, response value, and application-owned capabilities. Return the
engine output when the request negotiates `application/vnd.siren+json`.

```python
engine = siren(api.get_openapi_schema())

document = engine.project(
    SirenContext(
        base_url=request.build_absolute_uri("/"),
        resource="record",
        value=result,
        capabilities=capabilities_for(request, result),
    )
)

response_body = document.model_dump(by_alias=True, mode="json", exclude_none=True)
# Return response_body with Content-Type: application/vnd.siren+json.
```

Authorization and state remain application responsibilities. OpenAPI defines candidate actions;
`capabilities` determines which actions are advertised in this response.

## Deterministic rejections

Only root `sirenity` imports are supported. There is no public builder or internal-engine
construction path in version 2. Call `siren(openapi)` once at startup and handle the stable public
error types at the boundary:

```python
from sirenity import SirenityError, siren

try:
    engine = siren(openapi)
except SirenityError:
    # Invalid OpenAPI or a source operation that official Siren cannot represent.
    raise

try:
    document = engine.project(context)
except SirenityError:
    # Invalid resource, capability, path value, or request context.
    raise
```

Required and nullable query or JSON-body controls compile as ordinary standard Siren fields;
their validation remains server-enforced because official Siren does not define `required` or
`nullable` field members. UUIDs, flat primitive arrays, repeated query parameters, scalar enums,
and unambiguous scalar compositions are also supported. Structured values, header and cookie
parameters, and a sole non-JSON request media type are delegated to the API contract and client
transport rather than emitted as non-standard Siren fields. Multiple non-JSON media types,
ambiguous compositions, unsupported string formats, and `HEAD`, `OPTIONS`, or `TRACE` operations
still fail during `siren(openapi)`. This lets consumers reject unsupported contracts before
deployment rather than receiving a partial Siren response.
