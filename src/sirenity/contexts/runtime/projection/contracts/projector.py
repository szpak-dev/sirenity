from abc import ABC, abstractmethod

from ....shared import SirenityError, SirenScope
from ...document.values.document import SirenDocument
from ..values.request import SirenProjectionRequest


class SirenScopeProjector(ABC):
    @abstractmethod
    def supports(self, scope: SirenScope) -> bool:
        raise SirenityError

    @abstractmethod
    def project(self, request: SirenProjectionRequest) -> SirenDocument:
        raise SirenityError
