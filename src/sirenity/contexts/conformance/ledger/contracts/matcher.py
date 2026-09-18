from abc import ABC, abstractmethod

from ....shared import SirenityError
from ...implementation import SirenCapability
from ...specification import SirenRequirement
from ..values.report import SirenConformanceReport


class SirenRequirementMatcher(ABC):
    @abstractmethod
    def match(
        self, requirements: tuple[SirenRequirement, ...], capabilities: tuple[SirenCapability, ...]
    ) -> SirenConformanceReport:
        raise SirenityError
