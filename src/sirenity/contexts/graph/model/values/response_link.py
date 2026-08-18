from collections.abc import Mapping

from sirenity.contexts.shared import BaseValue, SirenRelation, SirenScope


class SirenResponseLink(BaseValue):
    operation: str
    parameters: Mapping[str, str] = {}
    rel: tuple[SirenRelation, ...]
    scope: SirenScope
