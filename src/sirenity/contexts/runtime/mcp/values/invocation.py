from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue


class SirenMcpInvocation(BaseValue):
    operation_id: str
    arguments: Mapping[str, JsonValue] = Field(default_factory=dict)
