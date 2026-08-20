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
