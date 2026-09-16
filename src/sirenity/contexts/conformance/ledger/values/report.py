from ....shared import BaseValue
from .feature import SirenBddFeature
from .finding import SirenFinding


class SirenConformanceReport(BaseValue):
    findings: tuple[SirenFinding, ...]
    features: tuple[SirenBddFeature, ...]
