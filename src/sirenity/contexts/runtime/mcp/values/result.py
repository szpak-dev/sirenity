from collections.abc import Mapping

from pydantic import JsonValue

from sirenity.contexts.shared import BaseValue


class SirenMcpResult(BaseValue):
    structured_content: Mapping[str, JsonValue]
    is_error: bool = False
