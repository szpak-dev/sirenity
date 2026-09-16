from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue, SirenMediaType
from .delegated_input import SirenDelegatedInput
from .parameter_input import SirenParameterInput


class SirenInput(BaseValue):
    media_type: SirenMediaType | None = None
    definition: Mapping[str, JsonValue] = Field(default_factory=dict)
    official_fields: tuple[str, ...] = ()
    parameters: tuple[SirenParameterInput, ...] = ()
    delegated_inputs: tuple[SirenDelegatedInput, ...] = ()
