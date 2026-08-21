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
    """Resolve one immutable configuration for every supported integration.

    Install Sirenity with `python -m pip install sirenity`. The application supplies its OpenAPI
    provider, capability policy, authentication, and already-executed operation results. Sirenity
    owns compilation, source/public mount matching, normalized input placement, and Siren/error
    translation. It does not dispatch application operations, infer policy, or require callers to
    parse OpenAPI or inspect an adapter's engine.

    ### Framework-neutral adapter

    Create one configuration after application routes are registered. `source_path` is the mount
    declared by OpenAPI; `public_path` is the mount exposed by Siren. Pass the result of the one
    application execution to `respond()`:

    <!-- example:framework-neutral:start -->
    ```python
    from example_project.permissions import siren_policy

    from sirenity import SirenAdapterRequest, siren_configuration

    example_configuration = siren_configuration(
        openapi="example_project.api.openapi_schema",
        source_path="/api",
        public_path="/siren",
        policy="example_project.permissions.siren_policy",
        profiles=("sirenity.SirenStructuredFormProfile",),
    )
    example_adapter = example_configuration.adapter()
    example_application_result = {
        "example_resource_id": "example-resource-42",
        "title": "Updated example resource",
    }
    example_response = example_adapter.respond(SirenAdapterRequest(
        operation_id="update_example_resource",
        status=200,
        result=example_application_result,
        base_url="https://api.example.com",
        path_values={"example_resource_id": "example-resource-42"},
        policy=siren_policy(
            "update_example_resource",
            200,
            object(),
            example_application_result,
        ),
    ))
    ```
    <!-- example:framework-neutral:end -->

    Framework authentication and execution stay outside Sirenity. Adapter profiles are the public
    extension point for optional representation metadata; policy is the extension point for
    application authorization and exceptional representation selection. Contract and projection
    failures raise `SirenityError` or `SirenContractError` at this direct boundary.

    ### Standard Django installation

    Add the public middleware loader after Django's conditional-response middleware. Django calls
    the application view exactly once, while Sirenity negotiates JSON versus Siren and rewrites a
    matched `/siren` request to the compiled `/api` route for dispatch:

    <!-- example:django:start -->
    ```python
    MIDDLEWARE: list[str] = [
        "django.middleware.http.ConditionalGetMiddleware",
        "sirenity.SirenMiddleware",
    ]
    SIRENITY: dict[str, str | list[str]] = {
        "OPENAPI": "example_project.api.openapi_schema",
        "SOURCE_PATH": "/api",
        "PUBLIC_PATH": "/siren",
        "POLICY": "example_project.permissions.siren_policy",
        "PROFILES": ["sirenity.SirenStructuredFormProfile"],
    }
    ```
    <!-- example:django:end -->

    Mount the application's normal JSON routes below `/api`; no duplicate Siren URL configuration
    is needed. Django owns authentication, views, and response creation. The middleware owns only
    matched JSON/Siren negotiation and preserves structured application errors. A settings mapping
    creates a fresh configuration for each Django startup, autoreload process, and `override_settings`
    middleware construction. A supplied `SirenConfiguration` retains its exact caller-owned lifecycle;
    tests should construct middleware inside the matching settings lifecycle.

    ### Shared Django and MCP composition

    Hosts that expose standard Django middleware and MCP from the same process should construct one
    configuration, assign that exact value to ``SIRENITY``, and pass it to ``siren_mcp``. MCP
    operations include the compiled HTTP method and encoded same-origin source dispatch path;
    arguments are normalized into body, query, header, cookie, and path values before the
    caller-owned Django or WSGI executor dispatches once:

    <!-- example:django-mcp:start -->
    ```python
    from example_project.execution import ExampleMcpExecutor

    from sirenity import SirenMcpInvocation, siren_configuration, siren_mcp

    example_configuration = siren_configuration(
        openapi="example_project.api.openapi_schema",
        source_path="/api",
        public_path="/siren",
        policy="example_project.permissions.siren_policy",
        profiles=("sirenity.SirenStructuredFormProfile",),
    )
    MIDDLEWARE = ["sirenity.SirenMiddleware"]
    SIRENITY = example_configuration
    example_mcp = siren_mcp(example_configuration, executor=ExampleMcpExecutor())

    example_result = example_mcp.invoke(SirenMcpInvocation(
        operation_id="update_example_resource",
        arguments={
            "example_resource_id": "example-resource-42",
            "title": "Updated example resource",
            "metadata": {"source": "example"},
            "example_page": 2,
            "example_trace": "example-trace",
            "example_session": "example-session",
        },
    ))
    if example_result.is_error:
        raise RuntimeError(example_result.structured_content["detail"])

    example_failure = example_mcp.invoke(SirenMcpInvocation(
        operation_id="update_example_resource",
        arguments={
            "example_resource_id": "example-resource-42",
            "title": "Invalid example resource",
            "metadata": "not-an-object",
            "example_trace": "example-trace",
        },
    ))
    example_error = example_failure.structured_content if example_failure.is_error else None
    ```
    <!-- example:django-mcp:end -->

    The MCP host owns SDK registration and lifecycle. Register `example_mcp.tools()` and retain
    `example_mcp.catalogue_fingerprint`; when a new configuration lifecycle changes the fingerprint,
    register the new catalogue and emit the host's native `tools/list_changed` notification. Hosts
    without that notification reconnect or restart after deployment. Sirenity never creates the MCP
    server, stores credentials, retries execution, or mutates projected documents.

    All three journeys use only published `sirenity` root imports. The generated public reference is
    the compatibility surface; framework- or protocol-specific behavior beyond these seams belongs in
    caller adapters and policies.
    """

    declaration = SirenConfigurationDeclaration(
        openapi=openapi,
        source_path=source_path,
        public_path=public_path,
        policy=policy,
        profiles=profiles,
    )
    return application.container.get(SirenConfigurationResolver).resolve(declaration)
