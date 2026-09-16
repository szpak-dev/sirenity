from dataclasses import dataclass

from pydantic import JsonValue
from wireup import injectable

from ...compatibility.values.compilation import SirenCompilation
from ...compatibility.values.diagnostics import SirenDiagnostics
from ..contracts.source import SirenSource
from ..values.compilation_request import OpenApiCompilationRequest
from .builder import SirenBuilder
from .compiler import OpenApiOperationCompiler


@injectable(as_type=SirenSource)
@dataclass(frozen=True)
class OpenApiSource(SirenSource):
    builder: SirenBuilder
    compiler: OpenApiOperationCompiler

    def compile(
        self, schema: dict[str, JsonValue], source_path: str, public_path: str
    ) -> SirenCompilation | SirenDiagnostics:
        request = OpenApiCompilationRequest(
            document=schema,
            paths=schema["paths"],
            source_path=source_path,
            public_path=public_path,
        )
        compilation = self.compiler.compile(request)
        match compilation:
            case SirenDiagnostics():
                return compilation
            case _:
                return SirenCompilation(api=self.builder.build(compilation))
