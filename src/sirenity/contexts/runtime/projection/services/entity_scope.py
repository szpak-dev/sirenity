from dataclasses import dataclass

from wireup import injectable

from ....shared import SirenityError, SirenScope
from ...document import SirenDocument, SirenEmbeddedRepresentation, SirenLink
from ..contracts.entity import SirenEntityDocumentService
from ..contracts.projector import SirenScopeProjector
from ..contracts.relationship import SirenRelationshipDocumentService
from ..values.request import SirenProjectionRequest


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
        document = self.entities.entity(request.api, request.resource, request.value, request.context, request.rel)
        relationships = self.relationships.relationships(request.api, request.context)
        embedded = []
        links = []
        for relationship in relationships:
            match relationship:
                case SirenEmbeddedRepresentation():
                    embedded.append(relationship)
                case SirenLink():
                    links.append(relationship)
        match document:
            case SirenDocument():
                return document.model_copy(
                    update={
                        "entities": tuple(embedded) or None,
                        "links": (*(document.links or ()), *links),
                    }
                )
            case _:
                raise SirenityError("Siren entity projection produced an embedded representation")
