from collections.abc import Mapping

from pydantic import Field, model_validator

from ....shared import BaseValue, SirenScope
from .response_source_input import ResponseSourceInputDraft


class ResponseLinkDraft(BaseValue):
    operation_id: str = ""
    operation_ref: str = ""
    parameters: Mapping[str, str] = Field(default_factory=dict)
    rel: tuple[str, ...]
    scope: SirenScope
    source_inputs: tuple[ResponseSourceInputDraft, ...] = ()

    @model_validator(mode="after")
    def validate_target(self) -> "ResponseLinkDraft":
        if bool(self.operation_id) == bool(self.operation_ref):
            raise ValueError("A response link requires exactly one operation target")
        return self
