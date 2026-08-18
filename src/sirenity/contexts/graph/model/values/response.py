from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue

from sirenity.contexts.shared import BaseValue, SirenMediaType

from .response_link import SirenResponseLink


class SirenResponse(BaseValue):
    status: str
    media_type: SirenMediaType | None = None
    shape: Literal["object", "array", "empty"]
    definition: Mapping[str, JsonValue] | None = None
    links: tuple[SirenResponseLink, ...] = ()
