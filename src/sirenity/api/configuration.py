"""Shared configuration.

<!-- docs:order=30 -->
"""

from ..contexts.runtime.configuration import SirenConfiguration, SirenConfigurationResolver
from ..contexts.runtime.configuration.values import SirenConfigurationDeclaration
from ..wiring import application


def siren_configuration(
    openapi: str,
    *,
    source_path: str = "/",
    public_path: str = "/",
    policy: str,
    profiles: tuple[str, ...] = (),
) -> SirenConfiguration:
    """Resolve one immutable, shared Siren integration configuration.

    Pass dotted paths for an OpenAPI provider, explicit capability policy, and optional adapter
    profiles. Resolution and compilation occur exactly once when this configuration is created;
    ``adapter()`` and ``django(get_response)`` reuse that compiled graph for its lifetime.

    ```python
    from sirenity import siren_configuration

    configuration = siren_configuration(
        openapi="example_project.api.openapi_schema",
        source_path="/api",
        public_path="/siren",
        policy="example_project.permissions.siren_policy",
        profiles=("sirenity.SirenStructuredFormProfile",),
    )
    adapter = configuration.adapter()
    middleware = configuration.django(get_response)
    ```

    Use the same configuration for every supported integration. Django settings create a fresh
    configuration for each startup, autoreload, and overridden-settings lifecycle, so stale
    process-global graphs are never reused.
    """

    declaration = SirenConfigurationDeclaration(
        openapi=openapi,
        source_path=source_path,
        public_path=public_path,
        policy=policy,
        profiles=profiles,
    )
    return application.container.get(SirenConfigurationResolver).resolve(declaration)
