from collections.abc import Mapping

from pydantic import JsonValue

from ....shared import BaseValue


class SirenMcpTool(BaseValue):
    name: str
    title: str
    description: str
    input_schema: Mapping[str, JsonValue]
