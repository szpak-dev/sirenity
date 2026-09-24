from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue


class SirenMcpOperation(BaseValue):
    operation_id: str
    method: str
    dispatch_path: str
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    body: JsonValue
    query_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    header_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    cookie_values: Mapping[str, JsonValue] = Field(default_factory=dict)
