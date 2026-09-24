from abc import ABC, abstractmethod
from collections.abc import Mapping

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
        resource: SirenResource | None,
        value: Mapping[str, JsonValue],
        include_query: bool,
    ) -> SirenUri:
        raise SirenityError
