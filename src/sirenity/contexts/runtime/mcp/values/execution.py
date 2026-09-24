from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue


class SirenMcpExecution(BaseValue):
    status: int
    result: JsonValue
    base_url: str
    request_url: str = ""
    headers: Mapping[str, str] = Field(default_factory=dict)
