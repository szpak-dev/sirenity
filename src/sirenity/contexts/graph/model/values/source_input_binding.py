from typing import Literal

from pydantic import Field

from ....shared import BaseValue


class SirenSourceInputBinding(BaseValue):
    target_name: str = Field(min_length=1)
    target_location: Literal["path", "query", "body"]
    source_name: str = Field(min_length=1)
    source_location: Literal["path", "query", "body"]
