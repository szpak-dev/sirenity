from ....shared import BaseValue, SirenFieldType


class SirenField(BaseValue):
    name: str
    type: SirenFieldType
    values: tuple[str | int | float, ...] = ()
    title: str | None = None
    default: str | int | float | None = None
