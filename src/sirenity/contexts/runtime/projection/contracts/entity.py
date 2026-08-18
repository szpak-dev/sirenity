from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from sirenity.contexts.graph import SirenApi, SirenResource
from sirenity.contexts.shared import SirenityError, SirenRelation

from ...document import SirenDocument, SirenEmbeddedRepresentation
from ...request import SirenContext


class SirenEntityDocumentService(ABC):
    @abstractmethod
    def entity(
        self,
        api: SirenApi,
        resource: SirenResource,
        value: Mapping[str, Any],
        context: SirenContext,
        rel: tuple[SirenRelation, ...],
    ) -> SirenDocument | SirenEmbeddedRepresentation:
        raise SirenityError
