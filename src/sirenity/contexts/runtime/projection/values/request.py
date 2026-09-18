from collections.abc import Mapping

from pydantic import JsonValue

from ....graph import SirenApi, SirenResource
from ....shared import BaseValue, SirenRelation
from ...request import SirenContext


class SirenProjectionRequest(BaseValue):
    api: SirenApi
    context: SirenContext
    resource: SirenResource | None
    value: Mapping[str, JsonValue]
    rel: tuple[SirenRelation, ...] = ()
