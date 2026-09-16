from pydantic import Field

from ....shared import BaseValue, SirenityError
from .tool import SirenMcpTool


class SirenMcpToolCatalogue(BaseValue):
    contract_version: str
    fingerprint: str
    tools: tuple[SirenMcpTool, ...] = Field(default_factory=tuple)

    def tool(self, operation_id: str) -> SirenMcpTool:
        matches = tuple(tool for tool in self.tools if tool.name == operation_id)
        if len(matches) != 1:
            raise SirenityError(f"Siren MCP catalogue references unknown operation: {operation_id}")
        return matches[0]

    def snapshot(self) -> tuple[SirenMcpTool, ...]:
        return tuple(tool.model_copy(deep=True) for tool in self.tools)
