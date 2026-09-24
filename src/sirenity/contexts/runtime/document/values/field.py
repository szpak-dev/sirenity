from pydantic import Field, StrictFloat, StrictInt

from ....shared import BaseValue, SirenFieldType
from .field_value import SirenFieldValue


class SirenField(BaseValue):
    name: str
    type: SirenFieldType = SirenFieldType.default()
    title: str = Field(default="", exclude_if=lambda value: not value)
    value: str | StrictInt | StrictFloat | tuple[SirenFieldValue, ...] = Field(
        default="", exclude_if=lambda value: value == ""
    )
