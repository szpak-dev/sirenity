from sirenity.contexts.shared import BaseValue, SirenHttpMethod, SirenMediaType, SirenScope

from .input_draft import InputDraft
from .response_draft import ResponseDraft


class OperationDraft(BaseValue):
    resource: str | None
    scope: SirenScope
    name: str
    method: SirenHttpMethod
    path: str
    title: str | None = None
    description: str = ""
    media_type: SirenMediaType | None
    input: InputDraft | None = None
    responses: tuple[ResponseDraft, ...] = ()
