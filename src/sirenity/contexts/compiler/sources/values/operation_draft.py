from sirenity.contexts.graph import SirenField, SirenInput
from sirenity.contexts.shared import BaseValue, SirenHttpMethod, SirenMediaType, SirenScope

from .response_draft import ResponseDraft


class OperationDraft(BaseValue):
    resource: str | None
    scope: SirenScope
    name: str
    method: SirenHttpMethod
    path: str
    source_path: str
    title: str
    description: str
    media_type: SirenMediaType | None
    fields: tuple[SirenField, ...] = ()
    input: SirenInput | None = None
    responses: tuple[ResponseDraft, ...] = ()
