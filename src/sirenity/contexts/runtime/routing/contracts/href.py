from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Literal

from pydantic import JsonValue

from ....graph import SirenResource
from ....shared import SirenityError, SirenUri
from ... import SirenContext


class SirenHrefService(ABC):
    @abstractmethod
    def href(
        self,
        path: str,
        context: SirenContext,
        resource: SirenResource | Literal[""],
        value: Mapping[str, JsonValue],
        include_query: bool,
    ) -> SirenUri:
        raise SirenityError
