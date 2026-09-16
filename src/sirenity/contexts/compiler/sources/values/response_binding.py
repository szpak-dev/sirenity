from collections.abc import Mapping

from pydantic import Field

from ....shared import BaseValue


class ResponseBindingDraft(BaseValue):
    operation: str = Field(min_length=1)
    fields: Mapping[str, str]
