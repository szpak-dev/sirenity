from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from ..contexts.runtime.adapter import (
    SirenAllowAllPolicy,
    SirenCapabilityPolicy,
    SirenDjangoMiddleware,
)
from ..contexts.shared import SirenityError
from .adapter import siren_adapter


@dataclass(frozen=True)
class SirenMiddleware:
    """Install Siren through Django's standard middleware loader.

    Add the root import directly to Django settings. The OpenAPI target may be a mapping, a callable
    returning one, or a Django Ninja/Ninja Extra API exposing `get_openapi_schema()`. By default the
    middleware exposes every capability owned by the matched operation's compiled graph scope. An
    optional policy target may restrict those capabilities or override exceptional response semantics.
    Optional `PROFILES` dotted paths are instantiated once with the adapter.

    ```python
    # example_project/api.py
    from ninja_extra import ControllerBase, NinjaExtraAPI, api_controller, http_get
    api = NinjaExtraAPI()

    @api_controller("/articles")
    class ArticleController(ControllerBase):
        @http_get("/{article_id}", operation_id="get_article")
        def get_article(self, article_id: str) -> dict[str, str]:
            return {"article_id": article_id, "title": "One-line Siren"}

    api.register_controllers(ArticleController)

    def siren_openapi():
        return api.get_openapi_schema(path_prefix="/api")

    # settings.py
    MIDDLEWARE = [
        "django.middleware.http.ConditionalGetMiddleware",
        "sirenity.SirenMiddleware",
    ]
    SIRENITY = {
        "OPENAPI": "example_project.api.siren_openapi",
        "SOURCE_PATH": "/api",
        "PUBLIC_PATH": "/siren",
        "PROFILES": ["sirenity.SirenStructuredFormProfile"],
    }

    # urls.py
    from django.urls import path
    from example_project.api import api
    urlpatterns = [path("api/", api.urls)]
    ```

    Django constructs this class with only `get_response`. Each middleware instance resolves the current
    settings and compiles after importing the configured API, once, so autoreload processes and overridden
    test settings receive a fresh completed route catalogue without process-global adapter state. Invalid or
    premature configuration raises `SirenityError` during middleware startup.
    """

    get_response: Callable[[object], object]
    middleware: SirenDjangoMiddleware = field(init=False)

    def __post_init__(self):
        try:
            from django.conf import settings
            from django.utils.module_loading import import_string

            configuration = getattr(settings, "SIRENITY", None)
            if not isinstance(configuration, Mapping):
                raise SirenityError("SIRENITY must be a mapping")
            openapi_path = configuration.get("OPENAPI")
            policy_path = configuration.get("POLICY")
            if not isinstance(openapi_path, str) or not openapi_path:
                raise SirenityError(
                    "SIRENITY.OPENAPI must be a dotted import path")
            if policy_path is not None and (not isinstance(policy_path, str) or not policy_path):
                raise SirenityError(
                    "SIRENITY.POLICY must be a dotted import path")
            source_path = configuration.get("SOURCE_PATH", "/")
            public_path = configuration.get("PUBLIC_PATH", "/")
            if not isinstance(source_path, str) or not isinstance(public_path, str):
                raise SirenityError(
                    "SIRENITY source and public paths must be strings")
            profile_paths = configuration.get("PROFILES", ())
            if not isinstance(profile_paths, list | tuple) or any(
                not isinstance(path, str) or not path for path in profile_paths
            ):
                raise SirenityError(
                    "SIRENITY.PROFILES must be a sequence of dotted import paths"
                )

            try:
                openapi_source = import_string(openapi_path)
                if isinstance(openapi_source, Mapping):
                    openapi = openapi_source
                elif hasattr(openapi_source, "get_openapi_schema"):
                    openapi = openapi_source.get_openapi_schema()
                elif callable(openapi_source):
                    openapi = openapi_source()
                else:
                    raise SirenityError(
                        "must resolve to a mapping, callable, or Ninja API"
                    )
            except Exception as error:
                raise SirenityError(
                    f"SIRENITY.OPENAPI could not be loaded: {error}"
                ) from error
            if not isinstance(openapi, Mapping):
                raise SirenityError(
                    "SIRENITY.OPENAPI did not produce an OpenAPI mapping")

            policy = SirenAllowAllPolicy()
            if policy_path is not None:
                try:
                    policy = import_string(policy_path)
                    if isinstance(policy, type):
                        policy = policy()
                except Exception as error:
                    raise SirenityError(
                        f"SIRENITY.POLICY could not be loaded: {error}"
                    ) from error
            if not isinstance(policy, SirenCapabilityPolicy) and not callable(policy):
                raise SirenityError(
                    "SIRENITY.POLICY must resolve to a SirenCapabilityPolicy or callable"
                )

            profiles = []
            for profile_path in profile_paths:
                try:
                    profile = import_string(profile_path)
                    profiles.append(profile() if isinstance(
                        profile, type) else profile)
                except Exception as error:
                    raise SirenityError(
                        f"SIRENITY.PROFILES could not load {profile_path!r}: {error}"
                    ) from error

            try:
                adapter = siren_adapter(
                    openapi,
                    source_path=source_path,
                    public_path=public_path,
                    profiles=tuple(profiles),
                )
            except Exception as error:
                raise SirenityError(
                    f"SIRENITY.OPENAPI could not be compiled: {error}"
                ) from error
            if not adapter.routes:
                raise SirenityError(
                    "SIRENITY.OPENAPI has no registered operations; initialization may be premature"
                )
            middleware = SirenDjangoMiddleware(
                get_response=self.get_response,
                adapter=adapter,
                policy=policy,
            )
            object.__setattr__(self, "middleware", middleware)
        except Exception as error:
            raise SirenityError(
                f"Django Siren middleware startup failed: {error}") from error

    def __call__(self, request: object) -> object:
        return self.middleware(request)
