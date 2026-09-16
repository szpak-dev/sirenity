from abc import ABC, abstractmethod

from ....shared import SirenityError
from ..values.requirement import SirenRequirement


class SirenSpecification(ABC):
    @abstractmethod
    def requirements(self) -> tuple[SirenRequirement, ...]:
        raise SirenityError
