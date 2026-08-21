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

    Django Ninja consumers can declare Siren relationships on the source operation with the native
    ``openapi_extra`` argument. Add the standard OpenAPI Link Object beneath the generated response,
    bind target path parameters from the response body, and declare the Siren relation and scope:

    ```python
    @api.get(
        "/api/example_groups/{example_group_id}",
        description="Read an example group.",
        operation_id="get_example_group",
        response=ExampleGroup,
        summary="Read example group",
        openapi_extra={
            "responses": {
                200: {
                    "links": {
                        "example_resources": {
                            "operationId": "list_example_group_resources",
                            "parameters": {
                                "path.example_group_id": "$response.body#/example_group_id",
                            },
                            "x-sirenity": {"rel": "collection", "scope": "collection"},
                        }
                    }
                }
            }
        },
    )
    def get_example_group(request, example_group_id: str):
        return {"example_group_id": example_group_id}
    ```

    Django Ninja merges this declaration into its generated response without an OpenAPI wrapper or
    post-processing provider. Middleware construction validates the operation target, path bindings,
    runtime expression, relation, and scope while compiling that generated document. The declared
    relationship therefore needs no application Siren policy solely to appear in the representation.
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
