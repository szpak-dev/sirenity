from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue
from ...projection.values.continuation import SirenProjectedContinuation


class SirenAdapterResponse(BaseValue):
    status: int
    payload: Mapping[str, JsonValue]
    media_type: str = "application/vnd.siren+json"
    headers: Mapping[str, str] = Field(default_factory=dict)
    continuations: tuple[SirenProjectedContinuation, ...] = ()
