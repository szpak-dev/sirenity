from dataclasses import dataclass

from wireup import injectable

from ....shared import SirenHttpMethod, SirenRelation, SirenScope
from ... import SirenDocument, SirenHrefService, SirenLink
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
        title = request.context.title or request.api.root.title
        properties = dict(request.context.value)
        if request.api.root.version:
            properties["version"] = request.api.root.version
        links = [
            SirenLink(
                rel=("self",),
                href=self.hrefs.href(request.api.root.route.path, request.context, "", {}, True),
                title=title,
            )
        ]
        links.extend(
            SirenLink(
                rel=(SirenRelation.validate("collection"),),
                href=self.hrefs.href(resource.collection.path, request.context, resource, {}, False),
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
            self.actions.action(operations[name], request.context, "", {}, False)
            for name in request.api.root.operations
            if name in request.context.capabilities
        ]
        return SirenDocument(
            class_=("api", "entry-point"),
            title=title,
            properties=properties,
            links=tuple(links),
            actions=tuple(actions),
        )
