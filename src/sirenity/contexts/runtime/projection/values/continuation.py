from collections.abc import Mapping

from pydantic import JsonValue

from ....shared import BaseValue


class SirenProjectedContinuation(BaseValue):
    operation_id: str
    arguments: Mapping[str, JsonValue]
    href: str
