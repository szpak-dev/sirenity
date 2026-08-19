from dataclasses import dataclass


@dataclass(frozen=True)
class SirenConfigurationDeclaration:
    openapi: str
    source_path: str
    public_path: str
    policy: str
    profiles: tuple[str, ...]
