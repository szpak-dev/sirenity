from typing import Protocol, runtime_checkable

from ..values import SirenMcpExecution, SirenMcpOperation


@runtime_checkable
class SirenMcpExecutor(Protocol):
    """Execute one normalized MCP operation exactly once."""

    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution: ...
