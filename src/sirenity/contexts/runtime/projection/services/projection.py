from collections.abc import Sequence
from dataclasses import dataclass

from wireup import injectable

from ....graph import SirenApi, SirenResource
from ....shared import SirenityError, SirenScope
from ... import SirenCapabilityValidator, SirenContext, SirenDocument, SirenResourceResolver
from ..contracts.projector import SirenScopeProjector
from ..values.request import SirenProjectionRequest


@injectable
@dataclass(frozen=True)
class SirenProjectionService:
    projectors: Sequence[SirenScopeProjector]
    resources: SirenResourceResolver
    capabilities: SirenCapabilityValidator

    def project(self, api: SirenApi, context: SirenContext) -> SirenDocument:
        resource = "" if context.scope == SirenScope.ROOT else self.resources.resolve(api, context)
        return self.project_resource(api, context, resource)

    def project_resource(self, api: SirenApi, context: SirenContext, resource: SirenResource | str) -> SirenDocument:
        if resource:
            self.capabilities.validate(resource, context, "")
        candidates = [projector for projector in self.projectors if projector.supports(context.scope)]
        if len(candidates) != 1:
            raise SirenityError(f"Siren scope {context.scope!r} requires exactly one projector")
        return candidates[0].project(
            SirenProjectionRequest(
                api=api,
                context=context,
                resource=resource,
                value=context.value,
            )
        )
