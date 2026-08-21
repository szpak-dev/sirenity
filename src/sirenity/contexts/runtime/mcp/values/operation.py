from collections.abc import Mapping

from pydantic import Field, JsonValue

from sirenity.contexts.shared import BaseValue


class SirenMcpOperation(BaseValue):
    """Represent a validated HTTP dispatch target and arguments separated by placement."""

    operation_id: str
    method: str
    dispatch_path: str
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    body: JsonValue = None
    query_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    header_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    cookie_values: Mapping[str, JsonValue] = Field(default_factory=dict)
