from collections.abc import Mapping

from pydantic import JsonValue

from ....graph import SirenApi
from ....shared import BaseValue, SirenRelation
from ... import SirenContext
from .resource import SirenProjectionResource


class SirenProjectionRequest(BaseValue):
    api: SirenApi
    context: SirenContext
    resource: SirenProjectionResource
    value: Mapping[str, JsonValue]
    rel: tuple[SirenRelation, ...] = ()
