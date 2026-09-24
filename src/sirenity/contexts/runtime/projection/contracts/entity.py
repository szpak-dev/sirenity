from abc import ABC, abstractmethod
from collections.abc import Mapping

from pydantic import JsonValue

from ....graph import SirenApi, SirenResource
from ....shared import SirenityError, SirenRelation
from ... import SirenContext, SirenDocument, SirenEmbeddedRepresentation


class SirenEntityDocumentService(ABC):
    @abstractmethod
    def entity(
        self,
        api: SirenApi,
        resource: SirenResource,
        value: Mapping[str, JsonValue],
        context: SirenContext,
        rel: tuple[SirenRelation, ...],
    ) -> SirenDocument | SirenEmbeddedRepresentation:
        raise SirenityError
