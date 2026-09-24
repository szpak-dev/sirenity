from collections.abc import Mapping
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from ....shared import BaseValue, SirenMediaType
from .continuation import SirenContinuation
from .response_binding import SirenResponseBinding
from .response_item_link import SirenResponseItemLink
from .response_link import SirenResponseLink


class SirenResponse(BaseValue):
    status: str
    media_type: SirenMediaType = Field(default_factory=SirenMediaType.default)
    shape: Literal["object", "array", "empty"]
    definition: Mapping[str, JsonValue] = Field(default_factory=dict)
    links: tuple[SirenResponseLink, ...] = ()
    item_links: tuple[SirenResponseItemLink, ...] = ()
    continuations: tuple[SirenContinuation, ...] = ()
    bindings: tuple[SirenResponseBinding, ...] = ()

    @model_validator(mode="after")
    def validate_content(self) -> "SirenResponse":
        if self.shape == "empty":
            if self.supplies("media_type") or self.definition:
                raise ValueError("An empty Siren response cannot declare content")
        elif not self.supplies("media_type") or not self.definition:
            raise ValueError("A Siren content response requires media type and definition")
        return self
