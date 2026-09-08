from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from wireup import injectable

from sirenity.contexts.graph import SirenApi
from sirenity.contexts.shared import SirenityError

from ...compatibility import (
    SirenCompatibilityFinding,
    SirenCompatibilityReport,
    SirenCompilation,
    SirenDiagnostics,
)
from ...sources import SirenSource
from ..contracts import SirenApiAssembler


@injectable
@dataclass(frozen=True)
class SirenApiService:
    """Build a validated Siren API graph from one or more sources."""

    sources: Sequence[SirenSource]
    assembler: SirenApiAssembler

    def build(
        self, schema: dict[str, Any], source_path: str = "/", public_path: str = "/"
    ) -> SirenApi:
        compilation = self.compile(schema, source_path, public_path)
        if isinstance(compilation, SirenDiagnostics):
            raise SirenityError(compilation.findings[0].detail)
        return compilation.api

    def audit(self, schema: dict[str, Any]) -> SirenCompatibilityReport:
        compilation = self.compile(schema, "/", "/")
        findings = compilation.findings if isinstance(compilation, SirenDiagnostics) else ()
        return SirenCompatibilityReport(findings=findings)

    def compile(
        self, schema: dict[str, Any], source_path: str, public_path: str
    ) -> SirenCompilation | SirenDiagnostics:
        compilations = tuple(source.compile(schema, source_path, public_path) for source in self.sources)
        findings = tuple(
            finding
            for compilation in compilations
            if isinstance(compilation, SirenDiagnostics)
            for finding in compilation.findings
        )
        ordered = sorted(findings, key=lambda finding: (finding.location, finding.category))
        if ordered:
            return SirenDiagnostics(findings=tuple(ordered))
        try:
            api = self.assembler.assemble(
                tuple(compilation.api for compilation in compilations if isinstance(compilation, SirenCompilation))
            )
        except (SirenityError, ValueError) as error:
            return SirenDiagnostics(
                findings=(SirenCompatibilityFinding(
                    location="#",
                    category="graph",
                    detail=str(error),
                    remediation="Correct the conflicting normalized OpenAPI declarations.",
                ),),
            )
        return SirenCompilation(api=api)
