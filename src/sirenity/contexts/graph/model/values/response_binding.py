from collections.abc import Mapping

from sirenity.contexts.shared import BaseValue


class SirenResponseBinding(BaseValue):
    operation: str
    fields: Mapping[str, str]
