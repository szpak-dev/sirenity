from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from sirenity.contexts.graph import SirenResource
from sirenity.contexts.shared import SirenityError, SirenUri

from ...request import SirenContext


class SirenHrefService(ABC):
    @abstractmethod
    def href(
        self,
        path: str,
        context: SirenContext,
        resource: SirenResource | None,
        value: Mapping[str, Any] | None = None,
        include_query: bool = True,
    ) -> SirenUri:
        raise SirenityError
