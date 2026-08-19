from typing import Protocol

from ..values import SirenConfiguration, SirenConfigurationDeclaration


class SirenConfigurationResolver(Protocol):
    def resolve(self, declaration: SirenConfigurationDeclaration) -> SirenConfiguration: ...
