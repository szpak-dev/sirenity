from abc import ABC, abstractmethod
from pathlib import Path

from ....shared import SirenityError
from ..values.feature import SirenBddFeature


class SirenBddEvidenceReader(ABC):
    @abstractmethod
    def read(self, cucumber_report: Path, feature_directory: Path) -> tuple[SirenBddFeature, ...]:
        raise SirenityError
