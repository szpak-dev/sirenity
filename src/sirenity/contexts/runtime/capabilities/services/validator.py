from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenResource
from sirenity.contexts.shared import ModwireSirenError, SirenScope

from ...request import SirenContext
from ..contracts import SirenCapabilityValidator


@injectable(as_type=SirenCapabilityValidator)
@dataclass(frozen=True)
class SirenDefaultCapabilityValidator(SirenCapabilityValidator):
    def validate(self, resource: SirenResource, context: SirenContext, scope: SirenScope | None = None) -> None:
        supported = (
            set(resource.collection_operations)
            if scope == SirenScope.COLLECTION
            else set(resource.entity_operations)
            if scope == SirenScope.ENTITY
            else set(resource.collection_operations) | set(resource.entity_operations)
        )
        unknown = sorted(context.capabilities - supported)
        if unknown:
            raise ModwireSirenError(f"Siren context declares unsupported capabilities for {resource.name!r}: {unknown}")
