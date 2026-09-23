from collections.abc import Mapping

from pydantic import Field, model_validator

from ....shared import BaseValue, SirenScope
from .response_source_input import ResponseSourceInputDraft


class ResponseLinkDraft(BaseValue):
    operation_id: str | None = None
    operation_ref: str | None = None
    parameters: Mapping[str, str] = Field(default_factory=dict)
    rel: tuple[str, ...]
    scope: SirenScope
    source_inputs: tuple[ResponseSourceInputDraft, ...] = ()

    @model_validator(mode="after")
    def validate_target(self) -> "ResponseLinkDraft":
        if (self.operation_id is None) == (self.operation_ref is None):
            raise ValueError("A response link requires exactly one operation target")
        return self
