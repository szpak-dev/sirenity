from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenApi
from sirenity.contexts.shared import SirenityError

from ..values import SirenOperationInput


@injectable
@dataclass(frozen=True)
class SirenOperationInputService:
    def input(self, api: SirenApi, operation_id: str) -> SirenOperationInput | None:
        matches = [
            operation for operation in api.operations if operation.name == operation_id]
        if len(matches) != 1:
            raise SirenityError(
                f"Siren input references unknown operation: {operation_id}")
        return matches[0].input
