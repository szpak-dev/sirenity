from collections.abc import Mapping

from pydantic import Field, JsonValue

from sirenity.contexts.shared import BaseValue


class SirenMcpExecution(BaseValue):
    """Carry one caller-executed MCP operation result back to the bridge."""

    status: int
    result: JsonValue = None
    base_url: str
    request_url: str | None = None
    headers: Mapping[str, str] = Field(default_factory=dict)
