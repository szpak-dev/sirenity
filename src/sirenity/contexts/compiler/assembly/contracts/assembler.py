from abc import ABC, abstractmethod

from ....graph import SirenApi
from ....shared import SirenityError


class SirenApiAssembler(ABC):
    @abstractmethod
    def assemble(self, apis: tuple[SirenApi, ...]) -> SirenApi:
        raise SirenityError
