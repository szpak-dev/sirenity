from collections.abc import Mapping

from pydantic import JsonValue

from ....shared import BaseValue


class SirenProjectedNavigation(BaseValue):
    operation_id: str
    arguments: Mapping[str, JsonValue]
    href: str
