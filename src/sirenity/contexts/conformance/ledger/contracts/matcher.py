from abc import ABC, abstractmethod

from ....shared import SirenityError
from ...implementation.values.capability import SirenCapability
from ...specification.values.requirement import SirenRequirement
from ..values.report import SirenConformanceReport


class SirenRequirementMatcher(ABC):
    @abstractmethod
    def match(
        self, requirements: tuple[SirenRequirement, ...], capabilities: tuple[SirenCapability, ...]
    ) -> SirenConformanceReport:
        raise SirenityError
