# MCP integration

## `siren_mcp`

Expose every compiled OpenAPI operation as a correctly described MCP tool.

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

Keep the last registered ``catalogue_fingerprint`` in the caller-owned MCP host. When a new
configuration lifecycle has a different fingerprint, register ``tools()`` again and use the
host's native refresh mechanism. Hosts that support it emit ``tools/list_changed`` after
registration; for hosts without a refresh notification, reconnect or restart after deployment.
Sirenity version ``1`` fingerprints the deterministic operation-ID order, tool name, title,
description, and normalized input schema as canonical key-sorted UTF-8 JSON hashed with SHA-256.
A change to that meaning requires a new contract version.

```python
example_current_fingerprint = example_bridge.catalogue_fingerprint
if example_current_fingerprint != example_registered_fingerprint:
    example_host.register_tools(example_bridge.tools())
    example_host.notify_tools_list_changed()
    example_registered_fingerprint = example_current_fingerprint
```

``executor.execute(operation)`` receives normalized path, body, query, header, and cookie
values and returns one already-executed ``SirenMcpExecution`` with the application status,
result, and base URL. Sirenity calls it exactly once, supplies the configuration policy, and
never reparses OpenAPI or builds another graph.
