from abc import ABC, abstractmethod

from sirenity.contexts.conformance.implementation.values import SirenCapability
from sirenity.contexts.conformance.specification.values import SirenRequirement
from sirenity.contexts.shared import SirenityError

from ..values import SirenConformanceReport


class SirenRequirementMatcher(ABC):
    @abstractmethod
    def match(
        self, requirements: tuple[SirenRequirement, ...], capabilities: tuple[SirenCapability, ...]
    ) -> SirenConformanceReport:
        raise SirenityError
