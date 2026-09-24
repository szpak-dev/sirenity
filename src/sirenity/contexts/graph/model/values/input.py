from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue, SirenMediaType
from .delegated_input import SirenDelegatedInput
from .parameter_input import SirenParameterInput


class SirenInput(BaseValue):
    media_type: SirenMediaType = Field(default_factory=SirenMediaType.default)
    definition: Mapping[str, JsonValue] = Field(default_factory=dict)
    official_fields: tuple[str, ...] = ()
    parameters: tuple[SirenParameterInput, ...] = ()
    delegated_inputs: tuple[SirenDelegatedInput, ...] = ()

    @property
    def present(self) -> bool:
        return bool(
            self.supplies("media_type")
            or self.definition
            or self.official_fields
            or self.parameters
            or self.delegated_inputs
        )
