"""Siren compiler.

<!-- docs:order=10 -->
"""

import json
from collections.abc import Mapping
from typing import Any

from openapi_spec_validator import validate

from ..contexts.runtime.engine import SirenEngine
from ..contexts.shared import SirenContractError, SirenityError
from ..wiring import application


def siren(
    openapi: Mapping[str, Any], *, source_path: str = "/", public_path: str = "/"
) -> SirenEngine:
    """Compile a complete OpenAPI 3.1 document into a reusable Siren engine.

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
    `properties.version` value. Every operation needs a non-empty `summary`; it becomes the action
    title. Every scalar action-field schema and every successful object or array response schema
    needs a non-empty `title`; an array response also needs a non-empty title on its item schema.
    Titles are an explicit OpenAPI authoring requirement: Sirenity never derives them from operation
    IDs, URLs, DTO names, or property names.

    Resource titles come only from explicitly connected successful response schemas: an object
    schema on the exact entity route names an entity, while an array schema on the exact collection
    route names its collection and its item schema names embedded items and entities. A meaningful
    array title names the collection; framework-generated `Response` wrapper titles and item DTO
    titles do not replace the resource title for collection navigation. Self and root collection
    links reuse those compiled titles.

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
    property, supplies the item and self-link title before the compiled resource title. Collection
    title precedence is an explicit runtime title, a meaningful array-schema title, then the resource
    title. When operations declare different schema titles, the exact GET representation takes
    precedence, followed by other operations in OpenAPI declaration order.

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
    """

    if not isinstance(openapi, Mapping):
        raise SirenContractError(
            "#", "input", "OpenAPI document must be a mapping.")
    if not isinstance(source_path, str) or not source_path.startswith("/"):
        raise SirenContractError(
            "#/source_path", "input", "Siren source path must start with '/'.")
    if not isinstance(public_path, str) or not public_path.startswith("/"):
        raise SirenContractError(
            "#/public_path", "input", "Siren public path must start with '/'.")
    source_path = source_path.rstrip("/") or "/"
    public_path = public_path.rstrip("/") or "/"
    try:
        document = json.loads(json.dumps(openapi))
    except Exception as error:
        raise SirenContractError(
            "#", "input", "OpenAPI document must be JSON-compatible.") from error
    try:
        validate(document)
    except Exception as error:
        raise SirenContractError(
            "#", "openapi", "OpenAPI document does not conform to OpenAPI 3.1.") from error
    try:
        api = application.api_service().build(document, source_path, public_path)
        return application.engine_factory().create(api)
    except SirenContractError:
        raise
    except SirenityError as error:
        raise SirenContractError("#", "compilation", str(error)) from error
    except Exception as error:
        raise SirenContractError(
            "#", "compilation", "Sirenity could not compile the OpenAPI document.") from error
