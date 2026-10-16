# Expose typed MCP navigation

You already have an OpenAPI contract and an application that decides which operations a caller may use. The missing
piece is an MCP result that carries the next operation and its bound arguments without asking the client to parse a
rendered URL.

This tutorial compiles two read operations. Reading a dashboard returns a standard OpenAPI response link to its
primary record. Sirenity projects that relationship as both a Siren link and a typed `SirenMcpInvocation`.

Save the complete example as `typed_navigation.py`.

## Define the contract

The response link binds `record_id` from the dashboard result. `x-sirenity` supplies the Siren relationship and
target scope; operation identity and argument placement remain standard OpenAPI facts.

```python
from pydantic import JsonValue

from sirenity import (
    SirenAdapterPolicy,
    SirenMcpExecution,
    SirenMcpInvocation,
    SirenMcpOperation,
    siren_configuration,
    siren_mcp,
)

OPENAPI: dict[str, JsonValue] = {
    "openapi": "3.1.1",
    "info": {"title": "Dashboard API", "version": "1.0.0"},
    "paths": {
        "/api/dashboards/{dashboard_id}": {
            "parameters": [
                {
                    "name": "dashboard_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string", "title": "Dashboard identifier"},
                }
            ],
            "get": {
                "operationId": "get_dashboard",
                "summary": "Read dashboard",
                "description": "Return one dashboard.",
                "responses": {
                    "200": {
                        "description": "Dashboard",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Dashboard"}
                            }
                        },
                        "links": {
                            "primary_record": {
                                "operationId": "get_record",
                                "parameters": {
                                    "path.record_id": "$response.body#/primary_record_id"
                                },
                                "x-sirenity": {"rel": "item", "scope": "entity"},
                            }
                        },
                    }
                },
            },
        },
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
                                "schema": {"$ref": "#/components/schemas/Record"}
                            }
                        },
                    }
                },
            },
        },
    },
    "components": {
        "schemas": {
            "Dashboard": {
                "type": "object",
                "title": "Dashboard",
                "required": ["dashboard_id", "primary_record_id"],
                "properties": {
                    "dashboard_id": {"type": "string", "title": "Dashboard identifier"},
                    "primary_record_id": {"type": "string", "title": "Primary record identifier"},
                },
            },
            "Record": {
                "type": "object",
                "title": "Record",
                "required": ["record_id", "title"],
                "properties": {
                    "record_id": {"type": "string", "title": "Record identifier"},
                    "title": {"type": "string", "title": "Title"},
                },
            },
        }
    },
}
```

## Supply policy and execution

The policy belongs to the application. This example permits both reads. The executor also belongs to the application;
Sirenity gives it a normalized operation and invokes it exactly once.

```python
class CapabilityPolicy:
    def select(
        self,
        operation_id: str | None,
        status: int,
        request: object,
        result: JsonValue,
    ) -> SirenAdapterPolicy:
        return SirenAdapterPolicy(capabilities=frozenset({"get_dashboard", "get_record"}))


class ApplicationExecutor:
    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution:
        if operation.operation_id == "get_dashboard":
            result: JsonValue = {
                "dashboard_id": operation.path_values["dashboard_id"],
                "primary_record_id": "record-42",
            }
        else:
            result = {
                "record_id": operation.path_values["record_id"],
                "title": "Architecture",
            }
        return SirenMcpExecution(
            status=200,
            result=result,
            base_url="https://api.example.com",
        )
```

## Compile and navigate

Create one shared configuration, expose its operations through the MCP bridge, and invoke the dashboard read. The
result contains a bound invocation for `get_record`; the caller can execute it directly.

```python
def main() -> None:
    configuration = siren_configuration(
        openapi="typed_navigation.OPENAPI",
        source_path="/api",
        public_path="/siren",
        policy="typed_navigation.CapabilityPolicy",
        profiles=(),
    )
    bridge = siren_mcp(configuration, executor=ApplicationExecutor())

    dashboard = bridge.invoke(
        SirenMcpInvocation(
            operation_id="get_dashboard",
            arguments={"dashboard_id": "dashboard-7"},
        )
    )

    assert dashboard.follow_ups == (
        SirenMcpInvocation(
            operation_id="get_record",
            arguments={"record_id": "record-42"},
        ),
    )
    assert dashboard.structured_content["links"][-1] == {
        "rel": ["item"],
        "href": "https://api.example.com/siren/records/record-42",
        "title": "Record",
    }

    record = bridge.invoke(dashboard.follow_ups[0])

    assert record.structured_content["properties"] == {
        "record_id": "record-42",
        "title": "Architecture",
    }


if __name__ == "__main__":
    main()
```

Run it from the project containing the module:

```console
python typed_navigation.py
```

No output means every assertion passed. Remove `get_record` from the policy's capabilities and run the example again:
the Siren relationship remains part of the declared contract, while the executable MCP `follow_ups` tuple becomes
empty. The application still owns permission; Sirenity only exposes navigation that is both declared and permitted.

## Continue from here

Use the [MCP integration guide](../how-to/mcp.md) to connect the bridge to an MCP host and manage catalogue refresh.
Use [typed navigation after execution](../explanation/typed-navigation.md) to choose correctly among follow-ups,
continuations, and verifications.
