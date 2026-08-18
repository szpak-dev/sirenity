from abc import ABC, abstractmethod
from pathlib import Path

from sirenity.contexts.shared import SirenityError

from ..values import SirenBddFeature


class SirenBddEvidenceReader(ABC):
    @abstractmethod
    def read(self, cucumber_report: Path, feature_directory: Path) -> tuple[SirenBddFeature, ...]:
        raise SirenityError
