from dataclasses import dataclass

from wireup import injectable

from ....shared import SirenityError, SirenRelation, SirenScope
from ... import SirenDocument, SirenEmbeddedRepresentation, SirenHrefService, SirenLink
from ..contracts.action import SirenActionDocumentService
from ..contracts.entity import SirenEntityDocumentService
from ..contracts.projector import SirenScopeProjector
from ..contracts.relationship import SirenRelationshipDocumentService
from ..values.request import SirenProjectionRequest


@injectable(as_type=SirenScopeProjector, qualifier=SirenScope.COLLECTION)
@dataclass(frozen=True)
class SirenCollectionScopeProjector(SirenScopeProjector):
    actions: SirenActionDocumentService
    entities: SirenEntityDocumentService
    hrefs: SirenHrefService
    relationships: SirenRelationshipDocumentService

    def supports(self, scope: SirenScope) -> bool:
        return scope == SirenScope.COLLECTION

    def project(self, request: SirenProjectionRequest) -> SirenDocument:
        resource = request.resource.get()
        if resource is None:
            raise SirenityError("Siren collection projection requires a resource")
        relationships = self.relationships.relationships(request.api, request.context)
        item_entities = tuple(
            self.entities.entity(
                request.api,
                resource,
                item,
                request.context.model_copy(
                    update={
                        "title": (
                            request.context.item_titles[index]
                            if request.context.item_titles
                            else item.get("title") or item.get("name")
                        ),
                        "capabilities": request.context.item_capabilities[index]
                        if request.context.item_capabilities
                        else request.context.capabilities,
                    }
                ),
                (SirenRelation.validate("item"),),
            )
            for index, item in enumerate(request.context.items)
        )
        embedded = []
        links = []
        for relationship in relationships:
            match relationship:
                case SirenEmbeddedRepresentation():
                    embedded.append(relationship)
                case SirenLink():
                    links.append(relationship)
        title = request.context.title or resource.title
        return SirenDocument(
            class_=(SirenScope.COLLECTION, resource.resource_class),
            title=title,
            properties=request.context.value,
            entities=(*item_entities, *embedded),
            actions=tuple(
                self.actions.actions(
                    request.api, resource, SirenScope.COLLECTION, request.context, request.context.value
                )
            ),
            links=(
                SirenLink(
                    rel=("self",),
                    title=title,
                    href=self.hrefs.href(resource.collection.path, request.context, resource, {}, True),
                ),
                *links,
            ),
        )
