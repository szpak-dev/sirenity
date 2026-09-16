from abc import ABC, abstractmethod

from ....graph import SirenApi
from ...document.values.embedded_representation import SirenEmbeddedRepresentation
from ...document.values.link import SirenLink
from ...request.values.context import SirenContext


class SirenRelationshipDocumentService(ABC):
    @abstractmethod
    def relationships(
        self, api: SirenApi, context: SirenContext
    ) -> tuple[SirenLink | SirenEmbeddedRepresentation, ...]:
        raise NotImplementedError
