from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ..policy import SirenAdapterPolicy


@injectable
@dataclass(frozen=True)
class SirenAllowAllPolicy:
    """Permit every capability owned by the matched operation's compiled graph scope."""

    def select(self, operation_id: str | None, status: int, request: object, result: JsonValue) -> SirenAdapterPolicy:
        return SirenAdapterPolicy(all_capabilities=True)
