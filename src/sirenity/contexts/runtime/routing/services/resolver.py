from dataclasses import dataclass

from wireup import injectable

from ....graph import SirenApi, SirenResource
from ....shared import SirenityError
from ...request.values.context import SirenContext
from ..contracts.resolver import SirenResourceResolver


@injectable(as_type=SirenResourceResolver)
@dataclass(frozen=True)
class SirenDefaultResourceResolver(SirenResourceResolver):
    def resolve(self, api: SirenApi, context: SirenContext) -> SirenResource:
        if context.resource is None:
            raise SirenityError(f"Siren {context.scope} context requires a resource")
        candidates = [resource for resource in api.resources if resource.name == context.resource]
        if not candidates:
            raise SirenityError(f"Siren context references unknown resource: {context.resource}")
        if len(candidates) == 1:
            return candidates[0]
        values = set(context.value) | set(context.path_values)
        matches = [
            resource for resource in candidates if set(self.parameters(resource.collection.path)).issubset(values)
        ]
        if not matches:
            raise SirenityError(
                f"Siren context cannot select resource {context.resource!r}: provide parent path values"
            )
        longest = max(len(self.parameters(resource.collection.path)) for resource in matches)
        selected = [resource for resource in matches if len(self.parameters(resource.collection.path)) == longest]
        if len(selected) != 1:
            raise SirenityError(
                f"Siren context cannot select resource {context.resource!r}: matching routes are ambiguous"
            )
        return selected[0]

    def parameters(self, path: str) -> tuple[str, ...]:
        return tuple(segment[1:-1] for segment in path.split("/") if segment.startswith("{") and segment.endswith("}"))
