from dataclasses import dataclass
from pathlib import Path

from wireup import injectable

from ...implementation.contracts.implementation import SirenImplementation
from ...specification.contracts.specification import SirenSpecification
from ..contracts.evidence_reader import SirenBddEvidenceReader
from ..contracts.matcher import SirenRequirementMatcher
from ..values.report import SirenConformanceReport
from .renderer import SirenLedgerRenderer
from .verdict import SirenLedgerVerdict


@injectable
@dataclass(frozen=True)
class SirenConformanceService:
    specification: SirenSpecification
    implementation: SirenImplementation
    matcher: SirenRequirementMatcher
    evidence: SirenBddEvidenceReader
    renderer: SirenLedgerRenderer
    verdict: SirenLedgerVerdict

    def inspect(self, cucumber_report: Path, feature_directory: Path) -> SirenConformanceReport:
        structural = self.matcher.match(self.specification.requirements(), self.implementation.capabilities())
        return SirenConformanceReport(
            findings=structural.findings,
            features=self.evidence.read(cucumber_report, feature_directory),
        )

    def render(self, report: SirenConformanceReport) -> str:
        return self.renderer.render(report)

    def verify(self, report: SirenConformanceReport) -> None:
        self.verdict.verify(report)
