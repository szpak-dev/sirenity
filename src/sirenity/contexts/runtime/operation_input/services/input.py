from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenApi
from sirenity.contexts.shared import SirenityError

from ..values import SirenDelegatedInput, SirenOperationInput


@injectable
@dataclass(frozen=True)
class SirenOperationInputService:
    def input(self, api: SirenApi, operation_id: str) -> SirenOperationInput | None:
        matches = [
            operation for operation in api.operations if operation.name == operation_id]
        if len(matches) != 1:
            raise SirenityError(
                f"Siren input references unknown operation: {operation_id}")
        value = matches[0].input
        if value is None:
            return None
        return SirenOperationInput(
            media_type=value.media_type,
            definition=value.definition,
            official_fields=value.official_fields,
            delegated_inputs=tuple(
                SirenDelegatedInput(
                    name=item.name,
                    location=item.location,
                    kind=item.kind,
                    required=item.required,
                    media_type=item.media_type,
                    style=item.style,
                    explode=item.explode,
                    allow_reserved=item.allow_reserved,
                    definition=item.definition,
                )
                for item in value.delegated_inputs
            ),
        )
