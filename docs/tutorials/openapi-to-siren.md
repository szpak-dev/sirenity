# Compile an OpenAPI document into Siren

You already have an OpenAPI document and application data. The missing piece is a response that tells a client not
only what the resource contains, but what it may do next.

This tutorial compiles one entity route and projects a record through it. The application decides which operations
are available. Sirenity turns that decision into links and actions.

## Define the contract

Create a complete OpenAPI 3.1 document with stable operation identifiers and explicit titles:

```python
openapi = {
    "openapi": "3.1.1",
    "info": {"title": "Records API", "version": "1.0.0"},
    "paths": {
        "/api/records/{record_id}": {
            "parameters": [
                {
                    "name": "record_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string", "title": "Record identifier"},
                }
            ],
            "get": {
                "operationId": "get_record",
                "summary": "Read record",
                "description": "Return one record.",
                "responses": {
                    "200": {
                        "description": "Record",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "title": "Record",
                                    "required": ["id", "title"],
                                    "properties": {
                                        "id": {"type": "string", "title": "Identifier"},
                                        "title": {"type": "string", "title": "Title"},
                                    },
                                }
                            }
                        },
                    }
                },
            },
            "patch": {
                "operationId": "rename_record",
                "summary": "Rename record",
                "description": "Replace the record title.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["title"],
                                "properties": {
                                    "title": {"type": "string", "title": "Title"}
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Renamed record",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "title": "Record",
                                    "required": ["id", "title"],
                                    "properties": {
                                        "id": {"type": "string", "title": "Identifier"},
                                        "title": {"type": "string", "title": "Title"},
                                    },
                                }
                            }
                        },
                    }
                },
            },
        }
    },
}
```

Sirenity compiles this document during startup. Invalid routes, ambiguous inputs, unsupported schemas, and broken
operation references fail here instead of leaking into request handling.

## Compile once

The source path is the mount described by OpenAPI. The public path is where clients see the Siren representation:

```python
from sirenity import SirenContext, siren

engine = siren(openapi, source_path="/api", public_path="/siren")
```

Keep the engine for the application lifecycle. It contains the normalized operation graph and does not need the
OpenAPI document again.

## Project one result

After the application has loaded the record and made its authorization decision, supply the value and the permitted
operation identifiers:

```python
document = engine.project(
    SirenContext(
        base_url="https://api.example.com",
        resource="record",
        value={"id": "record-42", "title": "Architecture"},
        capabilities=frozenset({"get_record", "rename_record"}),
    )
)

payload = document.model_dump(by_alias=True, mode="json", exclude_none=True)

assert payload["properties"] == {"id": "record-42", "title": "Architecture"}
assert {action["name"] for action in payload["actions"]} == {
    "get_record",
    "rename_record",
}
```

Remove `rename_record` from `capabilities` and project the same value again. The update action disappears; the
application data does not change. That is the central boundary: the application owns permission, while Sirenity
turns the permitted operation identifiers into concrete hypermedia controls.

## Continue from here

Use the [framework-neutral adapter](../how-to/adapter.md) when a framework has already executed the operation. Use
the [Django integration](../how-to/django.md) for standard middleware negotiation, or expose the same compiled graph
as [typed MCP tools](../how-to/mcp.md).
