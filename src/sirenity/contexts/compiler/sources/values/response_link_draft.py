from collections.abc import Mapping

from sirenity.contexts.shared import BaseValue, SirenScope


class ResponseLinkDraft(BaseValue):
    operation_id: str | None = None
    operation_ref: str | None = None
    parameters: Mapping[str, str] = {}
    rel: tuple[str, ...]
    scope: SirenScope
