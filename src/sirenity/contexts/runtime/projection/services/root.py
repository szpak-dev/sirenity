from dataclasses import dataclass

from wireup import injectable

from ....shared import SirenHttpMethod, SirenRelation, SirenScope
from ...document.values.document import SirenDocument
from ...document.values.link import SirenLink
from ...routing.contracts.href import SirenHrefService
from ..contracts.action import SirenActionDocumentService
from ..contracts.projector import SirenScopeProjector
from ..values.request import SirenProjectionRequest


@injectable(as_type=SirenScopeProjector, qualifier=SirenScope.ROOT)
@dataclass(frozen=True)
class SirenRootScopeProjector(SirenScopeProjector):
    actions: SirenActionDocumentService
    hrefs: SirenHrefService

    def supports(self, scope: SirenScope) -> bool:
        return scope == SirenScope.ROOT

    def project(self, request: SirenProjectionRequest) -> SirenDocument:
        operations = {operation.name: operation for operation in request.api.operations}
        title = request.context.title or request.api.root.title or None
        properties = dict(request.context.value)
        if request.api.root.version:
            properties["version"] = request.api.root.version
        links = [
            SirenLink(
                rel=("self",),
                href=self.hrefs.href(request.api.root.route.path, request.context, None),
                title=title,
            )
        ]
        links.extend(
            SirenLink(
                rel=(SirenRelation.validate("collection"),),
                href=self.hrefs.href(resource.collection.path, request.context, resource, include_query=False),
                title=resource.title,
            )
            for resource in request.api.resources
            if not any(
                segment.startswith("{") and segment.endswith("}") for segment in resource.collection.path.split("/")
            )
            and any(
                operation.scope == SirenScope.COLLECTION
                and operation.route.path == resource.collection.path
                and operation.method == SirenHttpMethod.GET
                for operation in request.api.operations
            )
        )
        actions = [
            self.actions.action(operations[name], request.context, None, {}, include_query=False)
            for name in request.api.root.operations
            if name in request.context.capabilities
        ]
        return SirenDocument(
            class_=("api", "entry-point"),
            title=title,
            properties=properties or None,
            links=tuple(links),
            actions=tuple(actions) or None,
        )
