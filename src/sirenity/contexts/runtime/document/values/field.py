from pydantic import StrictFloat, StrictInt

from ....shared import BaseValue, SirenFieldType
from .field_value import SirenFieldValue


class SirenField(BaseValue):
    name: str
    type: SirenFieldType = SirenFieldType.default()
    title: str | None = None
    value: str | StrictInt | StrictFloat | tuple[SirenFieldValue, ...] | None = None
