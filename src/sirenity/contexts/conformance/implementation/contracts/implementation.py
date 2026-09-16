from abc import ABC, abstractmethod

from ....shared import SirenityError
from ..values.capability import SirenCapability


class SirenImplementation(ABC):
    @abstractmethod
    def capabilities(self) -> tuple[SirenCapability, ...]:
        raise SirenityError
