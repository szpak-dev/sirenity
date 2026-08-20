from pydantic import Field

from sirenity.contexts.shared import BaseValue, SirenityError

from .tool import SirenMcpTool


class SirenMcpToolCatalogue(BaseValue):
    """Retain one versioned, immutable MCP tool contract for a configuration lifecycle."""

    contract_version: str
    fingerprint: str
    tools: tuple[SirenMcpTool, ...] = Field(default_factory=tuple)

    def tool(self, operation_id: str) -> SirenMcpTool:
        """Return the catalogue's sole tool for one compiled operation identifier."""

        matches = tuple(tool for tool in self.tools if tool.name == operation_id)
        if len(matches) != 1:
            raise SirenityError(f"Siren MCP catalogue references unknown operation: {operation_id}")
        return matches[0]

    def snapshot(self) -> tuple[SirenMcpTool, ...]:
        """Return defensive copies of the catalogue tools for caller-owned host registration."""

        return tuple(SirenMcpTool.model_validate(tool.model_dump(mode="json")) for tool in self.tools)
