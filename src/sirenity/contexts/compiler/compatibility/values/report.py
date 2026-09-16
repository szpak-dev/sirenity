from ....shared import BaseValue
from .finding import SirenCompatibilityFinding


class SirenCompatibilityReport(BaseValue):
    findings: tuple[SirenCompatibilityFinding, ...]

    @property
    def compatible(self) -> bool:
        return not self.findings

    def render(self) -> str:
        if self.compatible:
            return "OpenAPI-to-Siren compatibility: compatible"
        rows = (
            f"- {finding.location} [{finding.category}]: {finding.detail}. Remediation: {finding.remediation}"
            for finding in self.findings
        )
        return "OpenAPI-to-Siren compatibility findings:\n" + "\n".join(rows)
