from pydantic import JsonValue

from sirenity.api import SirenAdapterPolicy, SirenMcpExecution, SirenMcpOperation


class ExamplePolicy:
    def select(
        self,
        operation_id: str | None,
        status: int,
        request: object,
        result: JsonValue,
    ) -> SirenAdapterPolicy:
        return SirenAdapterPolicy(all_capabilities=True)


class ExampleInterruptedPolicy:
    def __init__(self):
        raise RuntimeError("example policy interrupted")


class ExampleExecutor:
    def __init__(self, executions: tuple[SirenMcpExecution, ...]):
        self.executions = executions
        self.calls: list[SirenMcpOperation] = []

    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution:
        self.calls.append(operation)
        return self.executions[len(self.calls) - 1]


class ExampleInterruptedExecutor:
    def __init__(self, recovery: SirenMcpExecution):
        self.recovery = recovery
        self.calls: list[SirenMcpOperation] = []

    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution:
        self.calls.append(operation)
        if len(self.calls) == 1:
            raise RuntimeError("example execution interrupted")
        return self.recovery


class ExampleRecordingPolicy:
    def __init__(self):
        self.calls: list[tuple[str | None, int, object, JsonValue]] = []

    def select(
        self,
        operation_id: str | None,
        status: int,
        request: object,
        result: JsonValue,
    ) -> SirenAdapterPolicy:
        self.calls.append((operation_id, status, request, result))
        return SirenAdapterPolicy(all_capabilities=True)
