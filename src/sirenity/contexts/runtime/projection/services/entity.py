from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ....graph import SirenApi, SirenResource
from ....shared import SirenRelation, SirenScope
from ... import SirenContext, SirenDocument, SirenEmbeddedRepresentation, SirenHrefService, SirenLink
from ..contracts.action import SirenActionDocumentService
from ..contracts.entity import SirenEntityDocumentService


@injectable(as_type=SirenEntityDocumentService)
@dataclass(frozen=True)
class SirenDefaultEntityDocumentService(SirenEntityDocumentService):
    actions: SirenActionDocumentService
    hrefs: SirenHrefService

    def entity(
        self,
        api: SirenApi,
        resource: SirenResource,
        value: Mapping[str, JsonValue],
        context: SirenContext,
        rel: tuple[SirenRelation, ...],
    ) -> SirenDocument | SirenEmbeddedRepresentation:
        title = context.title or resource.title
        fields = {
            "class_": (resource.resource_class,),
            "title": title,
            "properties": value,
            "actions": tuple(self.actions.actions(api, resource, SirenScope.ENTITY, context, value)),
            "links": (
                SirenLink(
                    rel=("self",),
                    title=title,
                    href=self.hrefs.href(
                        resource.entity.path if resource.entity.path else resource.collection.path,
                        context,
                        resource,
                        value,
                        True,
                    ),
                ),
            ),
        }
        if rel:
            return SirenEmbeddedRepresentation(rel=rel, **fields)
        return SirenDocument(**fields)
