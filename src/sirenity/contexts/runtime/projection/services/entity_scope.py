from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.shared import SirenityError, SirenScope

from ...document import SirenDocument, SirenEmbeddedRepresentation, SirenLink
from ..contracts import SirenEntityDocumentService, SirenRelationshipDocumentService, SirenScopeProjector
from ..state import SirenProjectionRequest


@injectable(as_type=SirenScopeProjector, qualifier=SirenScope.ENTITY)
@dataclass(frozen=True)
class SirenEntityScopeProjector(SirenScopeProjector):
    entities: SirenEntityDocumentService
    relationships: SirenRelationshipDocumentService

    def supports(self, scope: SirenScope) -> bool:
        return scope == SirenScope.ENTITY

    def project(self, request: SirenProjectionRequest) -> SirenDocument:
        if request.resource is None:
            raise SirenityError("Siren entity projection requires a resource")
        document = self.entities.entity(
            request.api, request.resource, request.value, request.context, request.rel)
        if isinstance(document, SirenDocument):
            relationships = self.relationships.relationships(
                request.api, request.context)
            embedded = tuple(value for value in relationships if isinstance(
                value, SirenEmbeddedRepresentation))
            links = tuple(
                value for value in relationships if isinstance(value, SirenLink))
            return document.model_copy(
                update={
                    "entities": embedded or None,
                    "links": (*(document.links or ()), *links),
                }
            )
        raise SirenityError(
            "Siren entity projection produced an embedded representation")
