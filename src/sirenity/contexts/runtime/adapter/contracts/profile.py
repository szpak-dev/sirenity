from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from ....graph import SirenInput
from ...request.values.response import SirenResponseContext


@runtime_checkable
class SirenAdapterProfile(Protocol):
    def apply(
        self,
        operation_id: str,
        operation_input: SirenInput | None,
        operation_inputs: Mapping[str, SirenInput | None],
        document: Mapping[str, JsonValue],
        context: SirenResponseContext,
    ) -> Mapping[str, JsonValue]: ...
