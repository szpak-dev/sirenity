from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue, model_validator

from ....shared import BaseValue, SirenMediaType


class SirenDelegatedInput(BaseValue):
    name: str
    location: Literal["query", "header", "cookie", "body"]
    kind: Literal["array", "object", "json"]
    required: bool = False
    media_type: SirenMediaType | Literal[""] = ""
    style: str = ""
    explode: bool = False
    allow_reserved: bool = False
    definition: Mapping[str, JsonValue]

    @model_validator(mode="after")
    def validate_transport_metadata(self) -> "SirenDelegatedInput":
        if self.location == "body":
            if not self.media_type:
                raise ValueError("Siren body input requires a media type")
            if self.style or self.explode:
                raise ValueError("Siren body input cannot define parameter serialization")
        elif self.media_type:
            raise ValueError("Siren parameter input cannot define a media type")
        elif not self.style:
            raise ValueError("Siren parameter input requires serialization metadata")
        return self
