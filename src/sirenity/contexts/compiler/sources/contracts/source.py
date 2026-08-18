from abc import ABC, abstractmethod
from typing import Any

from sirenity.contexts.graph import SirenApi
from sirenity.contexts.shared import SirenityError

from ...compatibility import SirenCompatibilityFinding


class SirenSource(ABC):
    @abstractmethod
    def load(self, schema: dict[str, Any], source_path: str, public_path: str) -> SirenApi:
        raise SirenityError

    @abstractmethod
    def audit(self, schema: dict[str, Any]) -> tuple[SirenCompatibilityFinding, ...]:
        raise SirenityError
