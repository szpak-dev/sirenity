from abc import ABC, abstractmethod
from typing import Any

from ...compatibility import SirenCompilation, SirenDiagnostics


class SirenSource(ABC):
    @abstractmethod
    def compile(
        self, schema: dict[str, Any], source_path: str, public_path: str
    ) -> SirenCompilation | SirenDiagnostics:
        raise NotImplementedError
