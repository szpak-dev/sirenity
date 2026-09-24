from pydantic import Field

from ....shared import BaseValue, SirenFieldType


class SirenField(BaseValue):
    name: str
    type: SirenFieldType
    values: tuple[str | int | float, ...] = ()
    title: str = Field(default="", exclude_if=lambda value: not value)
    default: str | int | float = ""
