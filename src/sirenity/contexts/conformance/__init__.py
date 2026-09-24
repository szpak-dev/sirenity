from importlib import import_module
from typing import Any, ClassVar


class _ConformanceExports:
    modules: ClassVar[dict[str, str]] = {
        "SirenCapability": ".implementation.values.capability",
        "SirenConformanceService": ".ledger.services.conformance",
        "SirenImplementation": ".implementation.contracts.implementation",
        "SirenRequirement": ".specification.values.requirement",
        "SirenSpecification": ".specification.contracts.specification",
    }

    def __call__(self, name: str) -> Any:
        module = import_module(self.modules[name], __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value


__getattr__ = _ConformanceExports()

__all__ = [
    "SirenCapability",
    "SirenConformanceService",
    "SirenImplementation",
    "SirenRequirement",
    "SirenSpecification",
]
