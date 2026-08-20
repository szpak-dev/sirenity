from collections.abc import Mapping

from pydantic import JsonValue, model_validator

from sirenity.contexts.shared import BaseValue, SirenMediaType

from .delegated_input import SirenDelegatedInput
from .parameter_input import SirenParameterInput


class SirenInput(BaseValue):
    media_type: SirenMediaType | None = None
    definition: Mapping[str, JsonValue] | None = None
    official_fields: tuple[str, ...] = ()
    parameters: tuple[SirenParameterInput, ...] = ()
    delegated_inputs: tuple[SirenDelegatedInput, ...] = ()

    @model_validator(mode="after")
    def validate_body_metadata(self) -> "SirenInput":
        if (self.media_type is None) != (self.definition is None):
            raise ValueError("Siren input media type and definition must be provided together")
        return self
