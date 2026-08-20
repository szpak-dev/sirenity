from collections.abc import Mapping

from pydantic import JsonValue

from sirenity.contexts.shared import BaseValue, SirenMediaType

from .delegated_input_draft import DelegatedInputDraft
from .parameter_input_draft import ParameterInputDraft


class InputDraft(BaseValue):
    media_type: SirenMediaType | None = None
    definition: Mapping[str, JsonValue] | None = None
    official_fields: tuple[str, ...] = ()
    parameters: tuple[ParameterInputDraft, ...] = ()
    delegated_inputs: tuple[DelegatedInputDraft, ...] = ()
