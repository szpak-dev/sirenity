from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue

from ....graph import SirenApi, SirenResource
from ....shared import BaseValue, SirenRelation
from ... import SirenContext


class SirenProjectionRequest(BaseValue):
    api: SirenApi
    context: SirenContext
    resource: SirenResource | Literal[""]
    value: Mapping[str, JsonValue]
    rel: tuple[SirenRelation, ...] = ()
