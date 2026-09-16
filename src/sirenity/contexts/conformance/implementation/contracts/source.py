from abc import ABC, abstractmethod

from ....shared import SirenityError
from ..values.capability import SirenCapability


class SirenContractSource(ABC):
    @abstractmethod
    def capabilities(self) -> tuple[SirenCapability, ...]:
        raise SirenityError
