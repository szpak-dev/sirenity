from abc import ABC, abstractmethod

from ....graph import SirenApi
from ... import SirenContext, SirenEmbeddedRepresentation, SirenLink


class SirenRelationshipDocumentService(ABC):
    @abstractmethod
    def relationships(
        self, api: SirenApi, context: SirenContext
    ) -> tuple[SirenLink | SirenEmbeddedRepresentation, ...]:
        raise NotImplementedError
