from abc import ABC, abstractmethod

from ....graph import SirenResource
from ....shared import SirenityError, SirenScope
from ...request import SirenContext


class SirenCapabilityValidator(ABC):
    @abstractmethod
    def validate(self, resource: SirenResource, context: SirenContext, scope: SirenScope | None = None) -> None:
        raise SirenityError
