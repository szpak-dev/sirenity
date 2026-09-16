from collections.abc import Mapping

from ....shared import BaseValue


class SirenResponseBinding(BaseValue):
    operation: str
    fields: Mapping[str, str]
