from dataclasses import dataclass

from wireup import injectable

from ....graph import SirenApi
from ....shared import SirenityError, SirenScope
from ... import (
    SirenCapabilityValidator,
    SirenContext,
    SirenEmbeddedRepresentation,
    SirenHrefService,
    SirenLink,
    SirenRelationship,
    SirenResourceResolver,
)
from ..contracts.entity import SirenEntityDocumentService
from ..contracts.relationship import SirenRelationshipDocumentService


@injectable(as_type=SirenRelationshipDocumentService)
@dataclass(frozen=True)
class SirenDefaultRelationshipDocumentService(SirenRelationshipDocumentService):
    capabilities: SirenCapabilityValidator
    entities: SirenEntityDocumentService
    hrefs: SirenHrefService
    resources: SirenResourceResolver

    def relationships(
        self, api: SirenApi, context: SirenContext
    ) -> tuple[SirenLink | SirenEmbeddedRepresentation, ...]:
        return tuple(self.relationship(api, context, relationship) for relationship in context.relationships)

    def relationship(
        self, api: SirenApi, context: SirenContext, relationship: SirenRelationship
    ) -> SirenLink | SirenEmbeddedRepresentation:
        related_context = context.model_copy(
            update={
                "scope": relationship.scope,
                "resource": relationship.resource,
                "title": relationship.title,
                "value": relationship.value,
                "items": (),
                "item_titles": (),
                "item_capabilities": (),
                "relationships": (),
                "path_values": relationship.path_values,
                "query": (),
                "capabilities": relationship.capabilities,
            }
        )
        resource = self.resources.resolve(api, related_context)
        self.capabilities.validate(resource, related_context, relationship.scope)
        path = (
            resource.collection.path
            if relationship.scope == SirenScope.COLLECTION or not resource.entity.path
            else resource.entity.path
        )
        if not relationship.embedded:
            return SirenLink(
                rel=relationship.rel,
                href=self.hrefs.href(path, related_context, resource, {}, True),
                title=relationship.title or resource.title,
            )
        if not resource.entity.path:
            raise SirenityError(f"Siren embedded relationship requires an entity resource: {resource.name}")
        document = self.entities.entity(api, resource, relationship.value, related_context, relationship.rel)
        match document:
            case SirenEmbeddedRepresentation():
                return document
            case _:
                raise SirenityError("Siren embedded relationship produced a document")
