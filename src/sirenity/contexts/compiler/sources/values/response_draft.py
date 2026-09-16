from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue

from ....shared import BaseValue, SirenMediaType
from .response_binding import ResponseBindingDraft
from .response_continuation import ResponseContinuationDraft
from .response_link_draft import ResponseLinkDraft


class ResponseDraft(BaseValue):
    status: str
    media_type: SirenMediaType | None = None
    shape: Literal["object", "array", "empty"]
    definition: Mapping[str, JsonValue] | None = None
    links: tuple[ResponseLinkDraft, ...] = ()
    continuations: tuple[ResponseContinuationDraft, ...] = ()
    bindings: tuple[ResponseBindingDraft, ...] = ()
