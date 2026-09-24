from collections.abc import Mapping
from typing import Literal

from pydantic import Field, JsonValue

from ....shared import BaseValue, SirenMediaType
from .response_binding import ResponseBindingDraft
from .response_continuation import ResponseContinuationDraft
from .response_item_link_draft import ResponseItemLinkDraft
from .response_link_draft import ResponseLinkDraft


class ResponseDraft(BaseValue):
    status: str
    media_type: SirenMediaType = Field(default_factory=SirenMediaType.default)
    shape: Literal["object", "array", "empty"]
    definition: Mapping[str, JsonValue] = Field(default_factory=dict)
    links: tuple[ResponseLinkDraft, ...] = ()
    item_links: tuple[ResponseItemLinkDraft, ...] = ()
    continuations: tuple[ResponseContinuationDraft, ...] = ()
    bindings: tuple[ResponseBindingDraft, ...] = ()
