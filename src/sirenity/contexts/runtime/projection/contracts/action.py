from abc import ABC, abstractmethod
from collections.abc import Mapping

from pydantic import JsonValue

from ....graph import SirenApi, SirenOperation, SirenResource
from ....shared import SirenityError, SirenScope
from ... import SirenAction, SirenContext


class SirenActionDocumentService(ABC):
    @abstractmethod
    def actions(
        self,
        api: SirenApi,
        resource: SirenResource,
        scope: SirenScope,
        context: SirenContext,
        value: Mapping[str, JsonValue],
    ) -> list[SirenAction]:
        raise SirenityError

    @abstractmethod
    def action(
        self,
        operation: SirenOperation,
        context: SirenContext,
        resource: SirenResource | None,
        value: Mapping[str, JsonValue],
        include_query: bool,
    ) -> SirenAction:
        raise SirenityError
