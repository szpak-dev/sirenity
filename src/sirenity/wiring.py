import fnmatch
import importlib
import pkgutil
from dataclasses import dataclass, field
from functools import cached_property
from types import ModuleType

from wireup import SyncContainer, create_sync_container


@dataclass(frozen=True)
class SirenServiceModuleDiscovery:
    package: str = "sirenity"

    def modules(self, patterns: tuple[str, ...]) -> list[ModuleType]:
        root = importlib.import_module(self.package)
        names = sorted(
            module.name
            for module in pkgutil.walk_packages(root.__path__, f"{root.__name__}.")
            if any(fnmatch.fnmatchcase(module.name, pattern) for pattern in patterns)
        )
        return [importlib.import_module(name) for name in names]


@dataclass(frozen=True)
class SirenApplication:
    discovery: SirenServiceModuleDiscovery = field(default_factory=SirenServiceModuleDiscovery)

    @cached_property
    def container(self) -> SyncContainer:
        return create_sync_container(injectables=self.discovery.modules(("sirenity.**.services",)))


application = SirenApplication()
