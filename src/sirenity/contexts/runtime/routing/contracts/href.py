from abc import ABC, abstractmethod
from collections.abc import Mapping

from pydantic import JsonValue

from ....graph import SirenResource
from ....shared import SirenityError, SirenUri
from ...request import SirenContext


class SirenHrefService(ABC):
    @abstractmethod
    def href(
        self,
        path: str,
        context: SirenContext,
        resource: SirenResource | None,
        value: Mapping[str, JsonValue] | None = None,
        include_query: bool = True,
    ) -> SirenUri:
        raise SirenityError
