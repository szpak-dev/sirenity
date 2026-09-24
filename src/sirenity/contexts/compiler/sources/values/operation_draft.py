from typing import Literal

from pydantic import Field

from ....graph import SirenField, SirenInput
from ....shared import BaseValue, SirenHttpMethod, SirenMediaType, SirenScope
from .response_draft import ResponseDraft


class OperationDraft(BaseValue):
    resource: str = ""
    scope: SirenScope
    name: str
    method: SirenHttpMethod
    path: str
    source_path: str
    title: str
    description: str
    media_type: SirenMediaType | Literal[""] = ""
    fields: tuple[SirenField, ...] = ()
    input: SirenInput = Field(default_factory=SirenInput)
    responses: tuple[ResponseDraft, ...] = ()
