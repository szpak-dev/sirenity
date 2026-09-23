from collections.abc import Mapping

from pydantic import Field

from ....shared import BaseValue, SirenRelation, SirenScope
from .source_input_binding import SirenSourceInputBinding


class SirenResponseLink(BaseValue):
    operation: str
    parameters: Mapping[str, str] = Field(default_factory=dict)
    rel: tuple[SirenRelation, ...]
    scope: SirenScope
    source_inputs: tuple[SirenSourceInputBinding, ...] = ()
