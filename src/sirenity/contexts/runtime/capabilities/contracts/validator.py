from abc import ABC, abstractmethod

from sirenity.contexts.graph import SirenResource
from sirenity.contexts.shared import ModwireSirenError, SirenScope

from ...request import SirenContext


class SirenCapabilityValidator(ABC):
    @abstractmethod
    def validate(self, resource: SirenResource, context: SirenContext, scope: SirenScope | None = None) -> None:
        raise ModwireSirenError
