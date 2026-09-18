from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue
from ...projection import SirenProjectedNavigation


class SirenAdapterResponse(BaseValue):
    status: int
    payload: Mapping[str, JsonValue]
    media_type: str = "application/vnd.siren+json"
    headers: Mapping[str, str] = Field(default_factory=dict)
    continuations: tuple[SirenProjectedNavigation, ...] = ()
    verifications: tuple[SirenProjectedNavigation, ...] = ()
