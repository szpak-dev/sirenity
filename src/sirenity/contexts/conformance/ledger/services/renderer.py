from dataclasses import dataclass

from wireup import injectable

from ..values.report import SirenConformanceReport


@injectable
@dataclass(frozen=True)
class SirenLedgerRenderer:
    def render(self, report: SirenConformanceReport) -> str:
        lines = ["Siren conformance ledger", "  Structural contract"]
        definition = None
        for finding in report.findings:
            if finding.requirement.definition != definition:
                definition = finding.requirement.definition
                lines.append(f"    {definition}")
            marker = "✓" if finding.implemented else "✗"
            lines.append(f"      {marker} {finding.requirement.label} — structural contract")
        lines.append("  Executable specification")
        for feature in report.features:
            lines.append(f"    {feature.name}")
            for scenario in feature.scenarios:
                marker = "✓" if scenario.implemented else "✗"
                evidence = "executable specification" if scenario.implemented else "expected failure"
                lines.append(f"      {marker} {scenario.name} — {evidence}")
        return "\n".join(lines)
