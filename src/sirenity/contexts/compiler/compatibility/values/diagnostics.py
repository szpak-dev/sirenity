from sirenity.contexts.shared import BaseValue

from .finding import SirenCompatibilityFinding


class SirenDiagnostics(BaseValue):
    findings: tuple[SirenCompatibilityFinding, ...]
