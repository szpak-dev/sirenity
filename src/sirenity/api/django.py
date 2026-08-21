"""Django integration.

<!-- docs:order=40 -->
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from ..contexts.runtime.adapter import SirenDjangoMiddleware
from ..contexts.runtime.configuration import SirenConfiguration
from ..contexts.shared import SirenityError
from .configuration import siren_configuration


@dataclass(frozen=True)
class SirenMiddleware:
    """Install Siren through Django's standard middleware loader.

    The loader consumes an exact immutable ``SirenConfiguration`` or turns the current ``SIRENITY``
    mapping into one, then installs middleware from that same configuration. Resolved settings
    declarations remain fresh for each Django startup, autoreload process, and ``override_settings``
    lifecycle; a supplied configuration retains its caller-owned adapter lifecycle. ``OPENAPI`` and
    ``POLICY`` are dotted import paths; ``PROFILES`` is an optional sequence of profile paths. A
    missing policy retains the standard allow-all behavior.
    """

    get_response: Callable[[object], object]
    middleware: SirenDjangoMiddleware = field(init=False)

    def __post_init__(self):
        try:
            from django.conf import settings

            configured = getattr(settings, "SIRENITY", None)
            if isinstance(configured, SirenConfiguration):
                selected = configured
            else:
                if not isinstance(configured, Mapping):
                    raise SirenityError("SIRENITY must be a SirenConfiguration or mapping")
                openapi = configured.get("OPENAPI")
                policy = configured.get("POLICY", "sirenity.SirenAllowAllPolicy")
                source_path = configured.get("SOURCE_PATH", "/")
                public_path = configured.get("PUBLIC_PATH", "/")
                profiles = configured.get("PROFILES", ())
                if not isinstance(openapi, str) or not openapi:
                    raise SirenityError("SIRENITY.OPENAPI must be a dotted import path")
                if not isinstance(policy, str) or not policy:
                    raise SirenityError("SIRENITY.POLICY must be a dotted import path")
                if not isinstance(source_path, str) or not isinstance(public_path, str):
                    raise SirenityError("SIRENITY source and public paths must be strings")
                if not isinstance(profiles, list | tuple) or any(
                    not isinstance(path, str) or not path for path in profiles
                ):
                    raise SirenityError("SIRENITY.PROFILES must be a sequence of dotted import paths")
                selected = siren_configuration(
                    openapi=openapi,
                    source_path=source_path,
                    public_path=public_path,
                    policy=policy,
                    profiles=tuple(profiles),
                )
            object.__setattr__(self, "middleware", selected.django(self.get_response))
        except Exception as error:
            raise SirenityError(f"Django Siren middleware startup failed: {error}") from error

    def __call__(self, request: object) -> object:
        return self.middleware(request)
