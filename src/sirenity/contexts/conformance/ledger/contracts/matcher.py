from abc import ABC, abstractmethod

from ....shared import SirenityError
from ... import SirenCapability, SirenRequirement
from ..values.report import SirenConformanceReport


class SirenRequirementMatcher(ABC):
    @abstractmethod
    def match(
        self, requirements: tuple[SirenRequirement, ...], capabilities: tuple[SirenCapability, ...]
    ) -> SirenConformanceReport:
        raise SirenityError
