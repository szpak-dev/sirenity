from copy import deepcopy

import pytest

from sirenity import (
    SirenAdapterRequest,
    SirenityError,
    SirenMcpExecution,
    SirenMcpInvocation,
    siren_configuration,
    siren_mcp,
)

mcp_openapi: dict[str, object] = {}


class ExampleMcpExecutor:
    def __init__(self, result: object = None):
        self.calls = []
        self.result = result

    def execute(self, operation):
        self.calls.append(operation)
        return SirenMcpExecution(
            status=200,
            result=self.result,
            base_url="https://api.example.com",
        )


def example_mcp_policy(*arguments):
    return None


def mcp_bridge(schema, executor=None, policy="sirenity.SirenAllowAllPolicy"):
    global mcp_openapi
    mcp_openapi = schema
    return siren_mcp(
        siren_configuration(
            openapi="tests.integration.test_mcp.mcp_openapi",
            policy=policy,
        ),
        executor=executor or ExampleMcpExecutor(),
    )


def test_public_mcp_bridge_exposes_compiled_operation_metadata_and_siren_content():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "operationId": "get_example_resource",
                    "summary": "Read example resource",
                    "description": "Read one example resource.",
                    "responses": {
                        "200": {
                            "description": "Example resource.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "Example resource",
                                        "properties": {"example_resource_id": {"type": "string"}},
                                    }
                                }
                            },
                        }
                    },
                },
            }
        },
    }
    bridge = mcp_bridge(schema)

    assert bridge.tools()[0].model_dump() == {
        "name": "get_example_resource",
        "title": "Read example resource",
        "description": "Read one example resource.",
        "input_schema": {
            "type": "object",
            "properties": {"example_resource_id": {"type": "string"}},
            "required": ["example_resource_id"],
            "additionalProperties": False,
        },
    }
    result = bridge.respond(
        SirenAdapterRequest(
            operation_id="get_example_resource",
            status=200,
            result={"example_resource_id": "42"},
            base_url="https://api.example.com",
            path_values={"example_resource_id": "42"},
        )
    )

    assert result.is_error is False
    assert result.structured_content["properties"] == {"example_resource_id": "42"}


def test_public_mcp_bridge_preserves_compiled_path_schema_and_rejects_name_collisions():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {
                        "name": "example_resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer", "minimum": 1},
                    }
                ],
                "get": {
                    "operationId": "get_example_resource",
                    "summary": "Read example resource",
                    "description": "Read one example resource.",
                    "responses": {"200": {"description": "Example resource."}},
                },
            }
        },
    }

    bridge = mcp_bridge(schema)

    assert bridge.tools()[0].input_schema["properties"]["example_resource_id"] == {"type": "integer", "minimum": 1}

    schema["paths"]["/example_resources/{example_resource_id}"]["get"]["parameters"] = [
        {"name": "example_resource_id", "in": "query", "schema": {"type": "string"}}
    ]

    with pytest.raises(SirenityError, match="cannot share a name"):
        mcp_bridge(schema)


def test_public_mcp_bridge_normalizes_compiled_input_placement():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "patch": {
                    "operationId": "update_example_resource",
                    "summary": "Update example resource",
                    "description": "Update one example resource.",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer", "title": "Page"}},
                        {"name": "trace", "in": "header", "required": True, "schema": {"type": "string"}},
                        {"name": "session", "in": "cookie", "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "metadata"],
                                    "properties": {
                                        "title": {"type": "string", "title": "Title"},
                                        "metadata": {"type": "object", "properties": {"source": {"type": "string"}}},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "Example resource."}},
                },
            }
        },
    }
    bridge = mcp_bridge(schema)

    operation = bridge.operation(
        SirenMcpInvocation(
            operation_id="update_example_resource",
            arguments={
                "example_resource_id": "example-example_resource-42",
                "page": 2,
                "trace": "example-trace",
                "session": "example-session",
                "title": "Example resource",
                "metadata": {"source": "example"},
            },
        )
    )

    assert operation.model_dump() == {
        "operation_id": "update_example_resource",
        "path_values": {"example_resource_id": "example-example_resource-42"},
        "body": {"title": "Example resource", "metadata": {"source": "example"}},
        "query_values": {"page": 2},
        "header_values": {"trace": "example-trace"},
        "cookie_values": {"session": "example-session"},
    }

    with pytest.raises(SirenityError, match="invalid arguments"):
        bridge.operation(
            SirenMcpInvocation(
                operation_id="update_example_resource",
                arguments={
                    "example_resource_id": "example-example_resource-42",
                    "trace": "example-trace",
                    "title": "Example resource",
                    "metadata": "not-an-object",
                },
            )
        )

    with pytest.raises(SirenityError, match="invalid arguments"):
        bridge.operation(
            SirenMcpInvocation(
                operation_id="update_example_resource",
                arguments={
                    "example_resource_id": 42,
                    "trace": "example-trace",
                    "title": "Example resource",
                    "metadata": {"source": "example"},
                },
            )
        )


@pytest.mark.parametrize(
    ("arguments", "message"),
    (({}, "missing required arguments"), ({"example_resource_id": "42", "unknown": "value"}, "unknown arguments")),
)
def test_public_mcp_bridge_rejects_invalid_compiled_inputs(arguments, message):
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "operationId": "get_example_resource",
                    "summary": "Read example resource",
                    "description": "Read one example resource.",
                    "responses": {
                        "200": {
                            "description": "Example resource.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "Example resource",
                                        "properties": {"example_resource_id": {"type": "string"}},
                                    }
                                },
                            },
                        }
                    },
                },
            }
        },
    }

    with pytest.raises(SirenityError, match=message):
        mcp_bridge(schema).operation(SirenMcpInvocation(operation_id="get_example_resource", arguments=arguments))


def test_public_mcp_bridge_rejects_unknown_compiled_operation():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources": {
                "get": {
                    "operationId": "list_example_resources",
                    "summary": "List example resources",
                    "description": "List all example resources.",
                    "responses": {"200": {"description": "Example resources."}},
                }
            }
        },
    }

    with pytest.raises(SirenityError, match="unknown operation"):
        mcp_bridge(schema).operation(SirenMcpInvocation(operation_id="missing", arguments={}))


def test_public_mcp_bridge_translates_projection_errors_to_structured_content():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources": {
                "get": {
                    "operationId": "list_example_resources",
                    "summary": "List example resources",
                    "description": "List all example resources.",
                    "responses": {"200": {"description": "Example resources."}},
                }
            }
        },
    }

    result = mcp_bridge(schema).respond(
        SirenAdapterRequest(
            operation_id="missing",
            status=200,
            result={},
            base_url="https://api.example.com",
        )
    )

    assert result.is_error is True
    assert result.structured_content["detail"] == "Siren adapter response failed"


@pytest.mark.parametrize(
    ("member", "message"),
    (("summary", "requires a non-empty summary"), ("description", "requires a non-empty description")),
)
def test_public_mcp_bridge_rejects_missing_openapi_tool_metadata(member, message):
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources": {
                "get": {
                    "operationId": "list_example_resources",
                    "summary": "List example resources",
                    "description": "List all example resources.",
                    "responses": {"200": {"description": "Example resources."}},
                }
            }
        },
    }
    del schema["paths"]["/example_resources"]["get"][member]

    with pytest.raises(SirenityError, match=message):
        mcp_bridge(schema)


def test_public_mcp_bridge_executes_once_through_shared_configuration():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {
                        "name": "example_resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "patch": {
                    "operationId": "update_example_resource",
                    "summary": "Update example resource",
                    "description": "Update one example resource.",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer", "title": "Page"}},
                        {
                            "name": "trace",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string", "title": "Trace"},
                        },
                        {"name": "session", "in": "cookie", "schema": {"type": "string", "title": "Session"}},
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title"],
                                    "properties": {"title": {"type": "string", "title": "Title"}},
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Example resource.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "Example resource",
                                        "properties": {"title": {"type": "string"}},
                                    }
                                },
                            },
                        }
                    },
                },
            }
        },
    }
    executor = ExampleMcpExecutor(result={"title": "Example resource"})
    bridge = mcp_bridge(schema, executor)

    result = bridge.invoke(
        SirenMcpInvocation(
            operation_id="update_example_resource",
            arguments={
                "example_resource_id": "example-example_resource-42",
                "title": "Example resource",
                "page": 2,
                "trace": "example-trace",
                "session": "example-session",
            },
        )
    )

    assert len(executor.calls) == 1
    assert executor.calls[0].model_dump() == {
        "operation_id": "update_example_resource",
        "path_values": {"example_resource_id": "example-example_resource-42"},
        "body": {"title": "Example resource"},
        "query_values": {"page": 2},
        "header_values": {"trace": "example-trace"},
        "cookie_values": {"session": "example-session"},
    }
    assert result.is_error is False
    assert result.structured_content["properties"] == {"title": "Example resource"}


def test_public_mcp_catalogue_fingerprint_is_stable_across_configuration_lifecycles():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "Example MCP API", "version": "1"},
        "paths": {
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "operationId": "get_example_resource",
                    "summary": "Read example resource",
                    "description": "Read one example resource.",
                    "parameters": [
                        {
                            "name": "example_filter",
                            "in": "query",
                            "schema": {"type": "string", "title": "Example filter"},
                        },
                        {
                            "name": "example_limit",
                            "in": "query",
                            "schema": {"type": "integer", "title": "Example limit"},
                        },
                    ],
                    "responses": {"200": {"description": "Example resource."}},
                },
            }
        },
    }

    first = mcp_bridge(schema)
    second = mcp_bridge(deepcopy(schema))
    reordered = deepcopy(schema)
    reordered["paths"]["/example_resources/{example_resource_id}"]["get"]["parameters"].reverse()

    assert first.catalogue_fingerprint == second.catalogue_fingerprint
    assert first.catalogue_fingerprint == mcp_bridge(reordered).catalogue_fingerprint
    assert first.tools() == second.tools()
    first_tools = first.tools()
    first_tools[0].input_schema["properties"]["example_resource_id"]["type"] = "integer"
    assert first.tools()[0].input_schema["properties"]["example_resource_id"] == {"type": "string"}


def test_public_mcp_catalogue_fingerprint_changes_only_with_visible_contract_data():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "Example MCP API", "version": "1"},
        "paths": {
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "operationId": "get_example_resource",
                    "summary": "Read example resource",
                    "description": "Read one example resource.",
                    "responses": {"200": {"description": "Example resource."}},
                },
            }
        },
    }
    baseline = mcp_bridge(schema).catalogue_fingerprint
    summary = deepcopy(schema)
    summary["paths"]["/example_resources/{example_resource_id}"]["get"]["summary"] = "Inspect example resource"
    description = deepcopy(schema)
    description["paths"]["/example_resources/{example_resource_id}"]["get"]["description"] = (
        "Inspect one example resource."
    )
    operation = deepcopy(schema)
    operation["paths"]["/example_resources/{example_resource_id}"]["get"]["operationId"] = "inspect_example_resource"
    input_schema = deepcopy(schema)
    input_schema["paths"]["/example_resources/{example_resource_id}"]["parameters"][0]["schema"] = {"type": "integer"}

    assert baseline != mcp_bridge(summary).catalogue_fingerprint
    assert baseline != mcp_bridge(description).catalogue_fingerprint
    assert baseline != mcp_bridge(operation).catalogue_fingerprint
    assert baseline != mcp_bridge(input_schema).catalogue_fingerprint


def test_public_mcp_catalogue_fingerprint_excludes_executor_policy_and_runtime_result():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "Example MCP API", "version": "1"},
        "paths": {
            "/example_resources": {
                "get": {
                    "operationId": "list_example_resources",
                    "summary": "List example resources",
                    "description": "List all example resources.",
                    "responses": {"200": {"description": "Example resources."}},
                }
            }
        },
    }

    default = mcp_bridge(schema, executor=ExampleMcpExecutor(result={"status": "first"}))
    alternate = mcp_bridge(
        deepcopy(schema),
        executor=ExampleMcpExecutor(result={"status": "second"}),
        policy="tests.integration.test_mcp.example_mcp_policy",
    )

    assert default.catalogue_fingerprint == alternate.catalogue_fingerprint
