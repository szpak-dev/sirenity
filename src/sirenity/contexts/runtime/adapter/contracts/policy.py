from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from ..policy import SirenAdapterPolicy


@runtime_checkable
class SirenCapabilityPolicy(Protocol):
    def select(
        self, operation_id: str | None, status: int, request: object, result: JsonValue
    ) -> SirenAdapterPolicy: ...
