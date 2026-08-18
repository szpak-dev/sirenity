from abc import ABC, abstractmethod

from sirenity.contexts.shared import SirenityError, SirenScope

from ...document import SirenDocument
from ..state import SirenProjectionRequest


class SirenScopeProjector(ABC):
    @abstractmethod
    def supports(self, scope: SirenScope) -> bool:
        raise SirenityError

    @abstractmethod
    def project(self, request: SirenProjectionRequest) -> SirenDocument:
        raise SirenityError
