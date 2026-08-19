from collections.abc import Mapping

from pydantic import Field, JsonValue

from sirenity.contexts.shared import BaseValue


class SirenMcpOperation(BaseValue):
    """Represent compiled MCP arguments separated by their HTTP placement."""

    operation_id: str
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    body: JsonValue = None
    query_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    header_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    cookie_values: Mapping[str, JsonValue] = Field(default_factory=dict)
