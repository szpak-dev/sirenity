import pytest

from sirenity import SirenAdapterRequest, SirenityError, siren_adapter, siren_mcp


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
    bridge = siren_mcp(siren_adapter(schema))

    assert bridge.tools()[0].model_dump() == {
        "name": "get_record",
        "title": "Read record",
        "description": "Read one record.",
        "input_schema": {"type": "object"},
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
        siren_mcp(siren_adapter(schema))
