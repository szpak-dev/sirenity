from abc import ABC, abstractmethod
from typing import Literal

from ....graph import SirenResource
from ....shared import SirenityError, SirenScope
from ... import SirenContext


class SirenCapabilityValidator(ABC):
    @abstractmethod
    def validate(self, resource: SirenResource, context: SirenContext, scope: SirenScope | Literal[""]) -> None:
        raise SirenityError
