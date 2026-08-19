from collections.abc import Mapping

from pydantic import Field, JsonValue

from sirenity.contexts.shared import BaseValue


class SirenMcpInvocation(BaseValue):
    """Describe arguments supplied to one compiled MCP operation tool."""

    operation_id: str
    arguments: Mapping[str, JsonValue] = Field(default_factory=dict)
