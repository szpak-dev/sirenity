from sirenity.contexts.shared import BaseValue, SirenFieldType


class Field(BaseValue):
    name: str
    type: SirenFieldType
    values: tuple[str | int | float, ...] = ()
    title: str
    default: str | int | float | None = None
