from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue

from sirenity.contexts.shared import BaseValue, SirenMediaType

from .response_link_draft import ResponseLinkDraft
from .runtime_binding_draft import RuntimeBindingDraft


class ResponseDraft(BaseValue):
    status: str
    media_type: SirenMediaType | None = None
    shape: Literal["object", "array", "empty"]
    definition: Mapping[str, JsonValue] | None = None
    links: tuple[ResponseLinkDraft, ...] = ()
    bindings: tuple[RuntimeBindingDraft, ...] = ()
