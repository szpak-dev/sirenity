from sirenity.contexts.runtime.adapter import SirenAdapter, SirenAdapterRequest
from sirenity.contexts.shared import BaseState, SirenContractError, SirenityError

from ..values import SirenMcpResult, SirenMcpTool


class SirenMcpBridge(BaseState):
    adapter: SirenAdapter

    def tools(self) -> tuple[SirenMcpTool, ...]:
        values = []
        for operation in self.adapter.engine.api.operations:
            input = self.adapter.engine.operation_input(operation.name)
            schema = input.definition if input is not None and input.definition is not None else {"type": "object"}
            values.append(SirenMcpTool(
                name=operation.name,
                title=operation.title,
                description=operation.description,
                input_schema=schema,
            ))
        return tuple(values)

    def respond(self, request: SirenAdapterRequest) -> SirenMcpResult:
        try:
            response = self.adapter.respond(request)
            return SirenMcpResult(structured_content=response.payload)
        except SirenContractError as error:
            return SirenMcpResult(
                structured_content={"location": error.location, "category": error.category, "detail": error.detail},
                is_error=True,
            )
        except SirenityError as error:
            return SirenMcpResult(structured_content={"detail": str(error)}, is_error=True)
