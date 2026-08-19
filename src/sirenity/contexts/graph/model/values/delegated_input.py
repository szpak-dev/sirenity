from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue, model_validator

from sirenity.contexts.shared import BaseValue, SirenMediaType


class SirenDelegatedInput(BaseValue):
    name: str
    location: Literal["query", "header", "cookie", "body"]
    kind: Literal["array", "object", "json"]
    required: bool = False
    media_type: SirenMediaType | None = None
    style: str | None = None
    explode: bool | None = None
    allow_reserved: bool = False
    definition: Mapping[str, JsonValue]

    @model_validator(mode="after")
    def validate_transport_metadata(self) -> "SirenDelegatedInput":
        if self.location == "body":
            if self.media_type is None:
                raise ValueError("Siren body input requires a media type")
            if self.style is not None or self.explode is not None:
                raise ValueError("Siren body input cannot define parameter serialization")
        elif self.media_type is not None:
            raise ValueError("Siren parameter input cannot define a media type")
        elif self.style is None or self.explode is None:
            raise ValueError("Siren parameter input requires serialization metadata")
        return self
