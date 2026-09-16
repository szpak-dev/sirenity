from abc import ABC, abstractmethod

from pydantic import JsonValue

from ...compatibility.values.compilation import SirenCompilation
from ...compatibility.values.diagnostics import SirenDiagnostics


class SirenSource(ABC):
    @abstractmethod
    def compile(
        self, schema: dict[str, JsonValue], source_path: str, public_path: str
    ) -> SirenCompilation | SirenDiagnostics:
        raise NotImplementedError
