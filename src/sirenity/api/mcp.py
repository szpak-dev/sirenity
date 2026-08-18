from ..contexts.runtime.adapter import SirenAdapter
from ..contexts.runtime.mcp import SirenMcpBridge


def siren_mcp(adapter: SirenAdapter) -> SirenMcpBridge:
    """Expose compiled Siren operation tools for a caller-owned MCP server."""

    return SirenMcpBridge(adapter=adapter)
