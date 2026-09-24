from pydantic import Field

from ....graph import SirenResource
from ....shared import BaseValue


class SirenProjectionResource(BaseValue):
    values: tuple[SirenResource, ...] = Field(default=(), max_length=1)

    def get(self) -> SirenResource | None:
        return self.values[0] if self.values else None
