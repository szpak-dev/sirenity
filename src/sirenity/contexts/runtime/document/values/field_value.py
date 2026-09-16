from pydantic import StrictFloat, StrictInt

from ....shared import BaseValue


class SirenFieldValue(BaseValue):
    value: str | StrictInt | StrictFloat
    title: str | None = None
    selected: bool = False
