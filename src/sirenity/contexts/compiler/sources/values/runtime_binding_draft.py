from collections.abc import Mapping

from sirenity.contexts.shared import BaseValue


class RuntimeBindingDraft(BaseValue):
    operation: str
    fields: Mapping[str, str]
