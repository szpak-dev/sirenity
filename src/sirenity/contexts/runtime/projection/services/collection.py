from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.shared import SirenityError, SirenRelation, SirenScope

from ...document import SirenDocument, SirenEmbeddedRepresentation, SirenLink
from ...routing import SirenHrefService
from ..contracts import (
    SirenActionDocumentService,
    SirenEntityDocumentService,
    SirenRelationshipDocumentService,
    SirenScopeProjector,
)
from ..state import SirenProjectionRequest


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
        if request.resource is None:
            raise SirenityError(
                "Siren collection projection requires a resource")
        relationships = self.relationships.relationships(
            request.api, request.context)
        item_entities = tuple(
            self.entities.entity(
                request.api,
                request.resource,
                item,
                request.context.model_copy(update={
                    "title": (
                        request.context.item_titles[index]
                        if request.context.item_titles
                        else item["title"]
                        if isinstance(item.get("title"), str) and item["title"].strip()
                        else item["name"]
                        if isinstance(item.get("name"), str) and item["name"].strip()
                        else None
                    ),
                    "capabilities": request.context.item_capabilities[index]
                    if request.context.item_capabilities else request.context.capabilities,
                }),
                (SirenRelation.validate("item"),),
            )
            for index, item in enumerate(request.context.items)
        )
        embedded = tuple(value for value in relationships if isinstance(
            value, SirenEmbeddedRepresentation))
        links = tuple(
            value for value in relationships if isinstance(value, SirenLink))
        title = request.context.title or request.resource.title
        return SirenDocument(
            class_=(SirenScope.COLLECTION, request.resource.resource_class),
            title=title,
            properties=request.context.value,
            entities=(*item_entities, *embedded) or None,
            actions=tuple(self.actions.actions(
                request.api, request.resource, SirenScope.COLLECTION, request.context, request.context.value
            )) or None,
            links=(
                SirenLink(
                    rel=("self",),
                    title=title,
                    href=self.hrefs.href(
                        request.resource.collection.path, request.context, request.resource),
                ),
                *links,
            ),
        )
