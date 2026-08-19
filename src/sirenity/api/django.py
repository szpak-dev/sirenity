"""Django integration.

<!-- docs:order=40 -->
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from ..contexts.runtime.adapter import SirenDjangoMiddleware
from ..contexts.shared import SirenityError
from .configuration import siren_configuration


@dataclass(frozen=True)
class SirenMiddleware:
    """Install Siren through Django's standard middleware loader.

    The loader turns the current ``SIRENITY`` settings into one immutable public configuration,
    then installs middleware from that same configuration. Each Django startup, autoreload process,
    and ``override_settings`` lifecycle therefore receives a fresh resolved configuration without a
    process-global adapter. ``OPENAPI`` and ``POLICY`` are dotted import paths; ``PROFILES`` is an
    optional sequence of profile paths. A missing policy retains the standard allow-all behavior.
    """

    get_response: Callable[[object], object]
    middleware: SirenDjangoMiddleware = field(init=False)

    def __post_init__(self):
        try:
            from django.conf import settings

            declaration = getattr(settings, "SIRENITY", None)
            if not isinstance(declaration, Mapping):
                raise SirenityError("SIRENITY must be a mapping")
            openapi = declaration.get("OPENAPI")
            policy = declaration.get("POLICY", "sirenity.SirenAllowAllPolicy")
            source_path = declaration.get("SOURCE_PATH", "/")
            public_path = declaration.get("PUBLIC_PATH", "/")
            profiles = declaration.get("PROFILES", ())
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
