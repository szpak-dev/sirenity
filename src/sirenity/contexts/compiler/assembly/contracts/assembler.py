from abc import ABC, abstractmethod

from sirenity.contexts.graph import SirenApi
from sirenity.contexts.shared import SirenityError


class SirenApiAssembler(ABC):
    @abstractmethod
    def assemble(self, apis: tuple[SirenApi, ...]) -> SirenApi:
        raise SirenityError
