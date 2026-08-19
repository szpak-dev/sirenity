from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue, model_validator

from sirenity.contexts.shared import BaseValue, SirenMediaType

from .response_binding import SirenResponseBinding
from .response_link import SirenResponseLink


class SirenResponse(BaseValue):
    status: str
    media_type: SirenMediaType | None = None
    shape: Literal["object", "array", "empty"]
    definition: Mapping[str, JsonValue] | None = None
    links: tuple[SirenResponseLink, ...] = ()
    bindings: tuple[SirenResponseBinding, ...] = ()

    @model_validator(mode="after")
    def validate_content(self) -> "SirenResponse":
        if self.shape == "empty":
            if self.media_type is not None or self.definition is not None:
                raise ValueError("An empty Siren response cannot declare content")
        elif self.media_type is None or self.definition is None:
            raise ValueError("A Siren content response requires media type and definition")
        return self
