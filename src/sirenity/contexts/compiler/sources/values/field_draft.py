from sirenity.contexts.shared import BaseValue, SirenFieldType


class FieldDraft(BaseValue):
    operation: str
    name: str
    type: SirenFieldType
    values: tuple[str | int | float, ...] = ()
    title: str
    default: str | int | float | None = None
