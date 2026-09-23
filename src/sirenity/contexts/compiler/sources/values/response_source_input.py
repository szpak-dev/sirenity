from pydantic import Field

from ....shared import BaseValue


class ResponseSourceInputDraft(BaseValue):
    target: str = Field(min_length=1)
    expression: str = Field(min_length=1)
