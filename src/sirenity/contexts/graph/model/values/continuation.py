from enum import StrEnum
from typing import Literal

from pydantic import Field

from ....shared import BaseValue
from .source_input_binding import SirenSourceInputBinding


class SirenContinuationKind(StrEnum):
    BOUNDED = "bounded"
    PAGINATION = "pagination"


class SirenContinuationParameter(BaseValue):
    name: str = Field(min_length=1)
    location: Literal["path", "query"]
    pointer: tuple[str, ...] = Field(min_length=1)


class SirenContinuation(BaseValue):
    operation: str = Field(min_length=1)
    kind: SirenContinuationKind
    parameters: tuple[SirenContinuationParameter, ...] = ()
    source_inputs: tuple[SirenSourceInputBinding, ...] = ()
