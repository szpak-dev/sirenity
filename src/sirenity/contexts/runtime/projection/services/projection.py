from collections.abc import Sequence
from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenApi, SirenResource
from sirenity.contexts.shared import SirenityError, SirenScope

from ...capabilities import SirenCapabilityValidator
from ...document import SirenDocument
from ...request import SirenContext
from ...routing import SirenResourceResolver
from ..contracts import SirenScopeProjector
from ..state import SirenProjectionRequest


@injectable
@dataclass(frozen=True)
class SirenProjectionService:
    projectors: Sequence[SirenScopeProjector]
    resources: SirenResourceResolver
    capabilities: SirenCapabilityValidator

    def project(self, api: SirenApi, context: SirenContext) -> SirenDocument:
        resource = None if context.scope == SirenScope.ROOT else self.resources.resolve(
            api, context)
        return self.project_resource(api, context, resource)

    def project_resource(
        self, api: SirenApi, context: SirenContext, resource: SirenResource | None
    ) -> SirenDocument:
        if resource is not None:
            self.capabilities.validate(resource, context)
        candidates = [
            projector for projector in self.projectors if projector.supports(context.scope)]
        if len(candidates) != 1:
            raise SirenityError(
                f"Siren scope {context.scope!r} requires exactly one projector")
        return candidates[0].project(SirenProjectionRequest(
            api=api,
            context=context,
            resource=resource,
            value=context.value,
        ))
