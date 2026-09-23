from typing import Literal

from pydantic import Field

from ....graph.model import SirenContinuationKind
from ....shared import BaseValue
from .response_source_input import ResponseSourceInputDraft


class ResponseOperationTarget(BaseValue):
    kind: Literal["operation_id", "operation_ref"]
    value: str = Field(min_length=1)


class ResponseContinuationParameter(BaseValue):
    name: str = Field(min_length=1)
    expression: str = Field(min_length=1)


class ResponseContinuationDraft(BaseValue):
    target: ResponseOperationTarget
    kind: SirenContinuationKind
    parameters: tuple[ResponseContinuationParameter, ...] = ()
    source_inputs: tuple[ResponseSourceInputDraft, ...] = ()
