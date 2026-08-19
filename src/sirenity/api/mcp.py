from ..contexts.runtime.adapter import SirenAdapter
from ..contexts.runtime.mcp import SirenMcpBridge


def siren_mcp(adapter: SirenAdapter) -> SirenMcpBridge:
    """Expose every compiled OpenAPI operation as a correctly described MCP tool.

    Turn each already-executed application result into Siren-aware MCP content. The caller owns
    the MCP SDK, server lifecycle, and application execution; this bridge owns neither.

    ```python
    from sirenity import SirenAdapterRequest, SirenMcpInvocation, siren_adapter, siren_mcp

    example_bridge = siren_mcp(siren_adapter(example_openapi))
    example_tools = example_bridge.tools()
    example_operation = example_bridge.operation(SirenMcpInvocation(
        operation_id="get_example_widget",
        arguments={"example_widget_id": "example-widget-42"},
    ))
    example_result = example_bridge.respond(SirenAdapterRequest(
        operation_id=example_operation.operation_id,
        status=200,
        result=example_application_result,
        base_url="https://example.invalid",
        path_values=example_operation.path_values,
    ))
    ```
    """

    return SirenMcpBridge(adapter=adapter)
