from collections.abc import Callable
from dataclasses import dataclass

from ...adapter import SirenAdapter, SirenCapabilityPolicy, SirenDjangoMiddleware
from ...mcp.values import SirenMcpToolCatalogue


@dataclass(frozen=True)
class SirenConfiguration:
    """Retain one resolved Siren adapter and policy for an application lifecycle."""

    adapter_value: SirenAdapter
    policy: SirenCapabilityPolicy | Callable[..., object]
    catalogue_value: SirenMcpToolCatalogue

    def adapter(self) -> SirenAdapter:
        """Return the configuration lifecycle's startup-compiled adapter."""

        return self.adapter_value

    def catalogue(self) -> SirenMcpToolCatalogue:
        """Return the configuration lifecycle's compiled MCP catalogue."""

        return self.catalogue_value

    def django(self, get_response: Callable[[object], object]) -> SirenDjangoMiddleware:
        """Build optional Django middleware over this configuration's adapter and policy."""

        return SirenDjangoMiddleware(
            get_response=get_response,
            adapter=self.adapter_value,
            policy=self.policy,
        )
