from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from sirenity.contexts.graph import SirenInput

from ...request import SirenResponseContext


@runtime_checkable
class SirenAdapterProfile(Protocol):
    """Extend a fresh adapter document using public normalized operation metadata.

    The adapter supplies the matched operation and input, a catalogue for every action operation, the
    projected response context, and a newly serialized document. Input values are deep copies, so a
    custom profile cannot mutate the cached engine graph. Return a JSON mapping for the next profile in
    the ordered pipeline; extension members are the profile's explicit non-standard contract.
    """

    def apply(
        self,
        operation_id: str,
        operation_input: SirenInput | None,
        operation_inputs: Mapping[str, SirenInput | None],
        document: Mapping[str, JsonValue],
        context: SirenResponseContext,
    ) -> Mapping[str, JsonValue]: ...
