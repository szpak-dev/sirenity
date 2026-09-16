from typing import Protocol, runtime_checkable

from ..values.execution import SirenMcpExecution
from ..values.operation import SirenMcpOperation


@runtime_checkable
class SirenMcpExecutor(Protocol):
    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution: ...
