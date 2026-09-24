from importlib import import_module
from typing import Any, ClassVar


class _CompilerExports:
    modules: ClassVar[dict[str, str]] = {
        "SirenApiService": ".assembly.services.api",
        "SirenCompatibilityFinding": ".compatibility.values.finding",
        "SirenCompatibilityReport": ".compatibility.values.report",
        "SirenCompilation": ".compatibility.values.compilation",
        "SirenDiagnostics": ".compatibility.values.diagnostics",
        "SirenSource": ".sources.contracts.source",
    }

    def __call__(self, name: str) -> Any:
        module = import_module(self.modules[name], __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value


__getattr__ = _CompilerExports()

__all__ = [
    "SirenApiService",
    "SirenCompatibilityFinding",
    "SirenCompatibilityReport",
    "SirenCompilation",
    "SirenDiagnostics",
    "SirenSource",
]
