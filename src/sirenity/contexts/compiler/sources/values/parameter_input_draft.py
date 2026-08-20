from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue

from sirenity.contexts.shared import BaseValue


class ParameterInputDraft(BaseValue):
    name: str
    location: Literal["path", "query", "header", "cookie"]
    required: bool
    definition: Mapping[str, JsonValue]
