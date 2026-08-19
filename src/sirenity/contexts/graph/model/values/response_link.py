from collections.abc import Mapping

from pydantic import Field

from sirenity.contexts.shared import BaseValue, SirenRelation, SirenScope


class SirenResponseLink(BaseValue):
    operation: str
    parameters: Mapping[str, str] = Field(default_factory=dict)
    rel: tuple[SirenRelation, ...]
    scope: SirenScope
