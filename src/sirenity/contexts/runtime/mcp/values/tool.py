from collections.abc import Mapping

from pydantic import JsonValue

from sirenity.contexts.shared import BaseValue


class SirenMcpTool(BaseValue):
    name: str
    title: str
    description: str
    input_schema: Mapping[str, JsonValue]
