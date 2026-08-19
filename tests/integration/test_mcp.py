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


def mcp_bridge(schema, executor=None):
    global mcp_openapi
    mcp_openapi = schema
    return siren_mcp(
        siren_configuration(
            openapi="tests.integration.test_mcp.mcp_openapi",
            policy="sirenity.SirenAllowAllPolicy",
        ),
        executor=executor or ExampleMcpExecutor(),
    )


def test_public_mcp_bridge_exposes_compiled_operation_metadata_and_siren_content():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {"/records/{record_id}": {
            "parameters": [{"name": "record_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "operationId": "get_record",
                "summary": "Read record",
                "description": "Read one record.",
                "responses": {"200": {"description": "Record", "content": {"application/json": {"schema": {
                    "type": "object", "title": "Record", "properties": {"record_id": {"type": "string"}}
                }}}}},
            },
        }},
    }
    bridge = mcp_bridge(schema)

    assert bridge.tools()[0].model_dump() == {
        "name": "get_record",
        "title": "Read record",
        "description": "Read one record.",
        "input_schema": {
            "type": "object",
            "properties": {"record_id": {"type": "string"}},
            "required": ["record_id"],
        },
    }
    result = bridge.respond(SirenAdapterRequest(
        operation_id="get_record",
        status=200,
        result={"record_id": "42"},
        base_url="https://api.example.com",
        path_values={"record_id": "42"},
    ))

    assert result.is_error is False
    assert result.structured_content["properties"] == {"record_id": "42"}


def test_public_mcp_bridge_normalizes_compiled_input_placement():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {"/widgets/{widget_id}": {
            "parameters": [{"name": "widget_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "patch": {
                "operationId": "update_widget",
                "summary": "Update widget",
                "description": "Update one widget.",
                "parameters": [
                    {"name": "page", "in": "query", "schema": {"type": "integer", "title": "Page"}},
                    {"name": "trace", "in": "header", "required": True,
                     "schema": {"type": "string"}},
                    {"name": "session", "in": "cookie", "schema": {"type": "string"}},
                ],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object", "required": ["title", "metadata"], "properties": {
                        "title": {"type": "string", "title": "Title"},
                        "metadata": {"type": "object", "properties": {"source": {"type": "string"}}},
                    },
                }}}},
                "responses": {"200": {"description": "Widget"}},
            },
        }},
    }
    bridge = mcp_bridge(schema)

    operation = bridge.operation(SirenMcpInvocation(
        operation_id="update_widget",
        arguments={
            "widget_id": "example-widget-42",
            "page": 2,
            "trace": "example-trace",
            "session": "example-session",
            "title": "Example widget",
            "metadata": {"source": "example"},
        },
    ))

    assert operation.model_dump() == {
        "operation_id": "update_widget",
        "path_values": {"widget_id": "example-widget-42"},
        "body": {"title": "Example widget", "metadata": {"source": "example"}},
        "query_values": {"page": 2},
        "header_values": {"trace": "example-trace"},
        "cookie_values": {"session": "example-session"},
    }

    with pytest.raises(SirenityError, match="invalid arguments"):
        bridge.operation(SirenMcpInvocation(
            operation_id="update_widget",
            arguments={
                "widget_id": "example-widget-42",
                "trace": "example-trace",
                "title": "Example widget",
                "metadata": "not-an-object",
            },
        ))

    with pytest.raises(SirenityError, match="invalid arguments"):
        bridge.operation(SirenMcpInvocation(
            operation_id="update_widget",
            arguments={
                "widget_id": 42,
                "trace": "example-trace",
                "title": "Example widget",
                "metadata": {"source": "example"},
            },
        ))


@pytest.mark.parametrize(
    ("arguments", "message"),
    (({}, "missing required arguments"),
     ({"record_id": "42", "unknown": "value"}, "unknown arguments")),
)
def test_public_mcp_bridge_rejects_invalid_compiled_inputs(arguments, message):
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {"/records/{record_id}": {
            "parameters": [{"name": "record_id", "in": "path", "required": True,
                            "schema": {"type": "string"}}],
            "get": {
                "operationId": "get_record",
                "summary": "Read record",
                "description": "Read one record.",
                "responses": {"200": {"description": "Record", "content": {
                    "application/json": {"schema": {
                        "type": "object", "title": "Record",
                        "properties": {"record_id": {"type": "string"}},
                    }},
                }}},
            },
        }},
    }

    with pytest.raises(SirenityError, match=message):
        mcp_bridge(schema).operation(SirenMcpInvocation(
            operation_id="get_record", arguments=arguments))


def test_public_mcp_bridge_rejects_unknown_compiled_operation():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {"/records": {"get": {
            "operationId": "list_records",
            "summary": "List records",
            "description": "List all records.",
            "responses": {"200": {"description": "Records"}},
        }}},
    }

    with pytest.raises(SirenityError, match="unknown operation"):
        mcp_bridge(schema).operation(SirenMcpInvocation(
            operation_id="missing", arguments={}))


def test_public_mcp_bridge_translates_projection_errors_to_structured_content():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {"/records": {"get": {
            "operationId": "list_records",
            "summary": "List records",
            "description": "List all records.",
            "responses": {"200": {"description": "Records"}},
        }}},
    }

    result = mcp_bridge(schema).respond(SirenAdapterRequest(
        operation_id="missing",
        status=200,
        result={},
        base_url="https://api.example.com",
    ))

    assert result.is_error is True
    assert result.structured_content["detail"] == "Siren adapter response failed"


@pytest.mark.parametrize(
    ("member", "message"),
    (("summary", "requires a non-empty summary"),
     ("description", "requires a non-empty description")),
)
def test_public_mcp_bridge_rejects_missing_openapi_tool_metadata(member, message):
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {"/records": {"get": {
            "operationId": "list_records",
            "summary": "List records",
            "description": "List all records.",
            "responses": {"200": {"description": "Records"}},
        }}},
    }
    del schema["paths"]["/records"]["get"][member]

    with pytest.raises(SirenityError, match=message):
        mcp_bridge(schema)


def test_public_mcp_bridge_executes_once_through_shared_configuration():
    schema = {
        "openapi": "3.1.1",
        "info": {"title": "MCP API", "version": "1"},
        "paths": {"/widgets/{widget_id}": {
            "parameters": [{
                "name": "widget_id", "in": "path", "required": True,
                "schema": {"type": "string"},
            }],
            "patch": {
                "operationId": "update_widget",
                "summary": "Update widget",
                "description": "Update one widget.",
                "parameters": [
                    {"name": "page", "in": "query", "schema": {
                        "type": "integer", "title": "Page"}},
                    {"name": "trace", "in": "header", "required": True,
                     "schema": {"type": "string", "title": "Trace"}},
                    {"name": "session", "in": "cookie", "schema": {
                        "type": "string", "title": "Session"}},
                ],
                "requestBody": {"required": True, "content": {"application/json": {"schema": {
                    "type": "object", "required": ["title"],
                    "properties": {"title": {"type": "string", "title": "Title"}},
                }}}},
                "responses": {"200": {"description": "Widget", "content": {
                    "application/json": {"schema": {
                        "type": "object", "title": "Widget",
                        "properties": {"title": {"type": "string"}},
                    }},
                }}},
            },
        }},
    }
    executor = ExampleMcpExecutor(result={"title": "Example widget"})
    bridge = mcp_bridge(schema, executor)

    result = bridge.invoke(SirenMcpInvocation(
        operation_id="update_widget",
        arguments={
            "widget_id": "example-widget-42",
            "title": "Example widget",
            "page": 2,
            "trace": "example-trace",
            "session": "example-session",
        },
    ))

    assert len(executor.calls) == 1
    assert executor.calls[0].model_dump() == {
        "operation_id": "update_widget",
        "path_values": {"widget_id": "example-widget-42"},
        "body": {"title": "Example widget"},
        "query_values": {"page": 2},
        "header_values": {"trace": "example-trace"},
        "cookie_values": {"session": "example-session"},
    }
    assert result.is_error is False
    assert result.structured_content["properties"] == {"title": "Example widget"}
