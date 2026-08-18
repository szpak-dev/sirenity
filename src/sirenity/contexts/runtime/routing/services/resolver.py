import re
from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenApi, SirenResource
from sirenity.contexts.shared import SirenityError

from ...request import SirenContext
from ..contracts import SirenResourceResolver

_PARAMETER = re.compile(r"\{([^}]+)\}")


@injectable(as_type=SirenResourceResolver)
@dataclass(frozen=True)
class SirenDefaultResourceResolver(SirenResourceResolver):
    def resolve(self, api: SirenApi, context: SirenContext) -> SirenResource:
        if context.resource is None:
            raise SirenityError(
                f"Siren {context.scope} context requires a resource")
        candidates = [
            resource for resource in api.resources if resource.name == context.resource]
        if not candidates:
            raise SirenityError(
                f"Siren context references unknown resource: {context.resource}")
        if len(candidates) == 1:
            return candidates[0]
        values = set(context.value) | set(context.path_values)
        matches = [
            resource
            for resource in candidates
            if set(_PARAMETER.findall(resource.collection.path)).issubset(values)
        ]
        if not matches:
            raise SirenityError(
                f"Siren context cannot select resource {context.resource!r}: provide parent path values"
            )
        longest = max(len(_PARAMETER.findall(resource.collection.path))
                      for resource in matches)
        selected = [resource for resource in matches if len(
            _PARAMETER.findall(resource.collection.path)) == longest]
        if len(selected) != 1:
            raise SirenityError(
                f"Siren context cannot select resource {context.resource!r}: matching routes are ambiguous"
            )
        return selected[0]
