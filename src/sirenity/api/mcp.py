"""MCP integration.

<!-- docs:order=50 -->
"""

from ..contexts.runtime.configuration import SirenConfiguration
from ..contexts.runtime.mcp import SirenMcpBridge, SirenMcpExecutor


def siren_mcp(configuration: SirenConfiguration, *, executor: SirenMcpExecutor) -> SirenMcpBridge:
    """Expose every compiled OpenAPI operation as a correctly described MCP tool.

    Derive MCP tools from a shared configuration and turn one executor result into Siren-aware MCP
    content. The caller owns the MCP SDK, server lifecycle, and application execution; this bridge
    owns neither.

    ```python
    from sirenity import SirenMcpExecution, SirenMcpInvocation, siren_configuration, siren_mcp

    example_configuration = siren_configuration(
        openapi="example_project.api.openapi_schema",
        source_path="/api",
        public_path="/siren",
        policy="example_project.permissions.siren_policy",
    )
    example_bridge = siren_mcp(example_configuration, executor=ExampleMcpExecutor())
    example_tools = example_bridge.tools()
    example_result = example_bridge.invoke(SirenMcpInvocation(
        operation_id="get_example_widget",
        arguments={"example_widget_id": "example-widget-42"},
    ))
    ```

    ``executor.execute(operation)`` receives normalized path, body, query, header, and cookie
    values and returns one already-executed ``SirenMcpExecution`` with the application status,
    result, and base URL. Sirenity calls it exactly once, supplies the configuration policy, and
    never reparses OpenAPI or builds another graph.
    """

    return SirenMcpBridge(
        adapter=configuration.adapter(), policy=configuration.policy, executor=executor)
