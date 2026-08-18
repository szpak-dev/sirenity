from abc import ABC, abstractmethod

from sirenity.contexts.shared import SirenityError

from ..values import SirenRequirement


class SirenSpecification(ABC):
    @abstractmethod
    def requirements(self) -> tuple[SirenRequirement, ...]:
        raise SirenityError
