import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pydantic import JsonValue, TypeAdapter
from wireup import injectable

from ....graph import SirenApi
from ....shared import SirenContractError, SirenityError
from ...compatibility import (
    SirenCompatibilityFinding,
    SirenCompatibilityReport,
    SirenCompilation,
    SirenDiagnostics,
)
from ...sources import SirenSource
from ..contracts.assembler import SirenApiAssembler


@injectable
@dataclass(frozen=True)
class SirenApiService:
    sources: Sequence[SirenSource]
    assembler: SirenApiAssembler

    def build(self, schema: dict[str, JsonValue], source_path: str = "/", public_path: str = "/") -> SirenApi:
        compilation = self.compile(schema, source_path, public_path)
        match compilation:
            case SirenDiagnostics(findings=findings):
                raise SirenityError(findings[0].detail)
            case SirenCompilation(api=api):
                return api

    def audit(self, schema: dict[str, JsonValue]) -> SirenCompatibilityReport:
        compilation = self.compile(schema, "/", "/")
        match compilation:
            case SirenDiagnostics(findings=findings):
                return SirenCompatibilityReport(findings=findings)
            case SirenCompilation():
                return SirenCompatibilityReport(findings=())

    def compile(
        self, schema: dict[str, JsonValue], source_path: str, public_path: str
    ) -> SirenCompilation | SirenDiagnostics:
        compilations = tuple(source.compile(schema, source_path, public_path) for source in self.sources)
        findings: list[SirenCompatibilityFinding] = []
        apis: list[SirenApi] = []
        for compilation in compilations:
            match compilation:
                case SirenDiagnostics(findings=diagnostics):
                    findings.extend(diagnostics)
                case SirenCompilation(api=api):
                    apis.append(api)
        ordered = sorted(findings, key=lambda finding: (finding.location, finding.category))
        if ordered:
            return SirenDiagnostics(findings=tuple(ordered))
        api = self.assembler.assemble(tuple(apis))
        return SirenCompilation(api=api)

    def normalize(self, openapi: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        paths = openapi.get("paths", {})
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
                    continue
                responses = operation.get("responses")
                if responses is None:
                    continue
                statuses: set[str] = set()
                for status in responses:
                    normalized = str(status)
                    if normalized in statuses:
                        escaped_path = str(path).replace("~", "~0").replace("/", "~1")
                        escaped_method = str(method).replace("~", "~0").replace("/", "~1")
                        location = f"#/paths/{escaped_path}/{escaped_method}/responses"
                        raise SirenContractError(
                            location,
                            "input",
                            f"OpenAPI operation declares duplicate response status: {normalized}",
                        )
                    statuses.add(normalized)
        return TypeAdapter(dict[str, JsonValue]).validate_json(json.dumps(openapi))
