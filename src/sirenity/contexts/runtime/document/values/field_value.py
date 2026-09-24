from pydantic import Field, StrictFloat, StrictInt

from ....shared import BaseValue


class SirenFieldValue(BaseValue):
    value: str | StrictInt | StrictFloat
    title: str = Field(default="", exclude_if=lambda value: not value)
    selected: bool = False
