from collections.abc import Mapping
from typing import Literal

from pydantic import Field, JsonValue, model_validator

from ....shared import BaseValue, SirenityError, SirenMediaType
from ..policy import SirenAdapterPolicy


class SirenAdapterRequest(BaseValue):
    status: int
    result: JsonValue
    base_url: str
    operation_id: str = ""
    method: str = ""
    path: str = ""
    request_url: str = ""
    media_type: SirenMediaType | Literal[""] = ""
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    query: tuple[tuple[str, JsonValue], ...] = ()
    body: JsonValue = Field(default_factory=dict)
    headers: Mapping[str, str] = Field(default_factory=dict)
    policy: SirenAdapterPolicy = Field(default_factory=SirenAdapterPolicy)

    @model_validator(mode="after")
    def validate_request(self) -> "SirenAdapterRequest":
        if not 100 <= self.status <= 599:
            raise SirenityError("Siren adapter status must be between 100 and 599")
        if not self.operation_id and (bool(self.method) != bool(self.path)):
            raise SirenityError("Siren adapter route resolution requires both method and path")
        if not self.operation_id and not self.path and self.status < 400:
            raise SirenityError("A successful Siren adapter response requires an operation")
        return self
