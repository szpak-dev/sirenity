from django.conf import settings
from django.http import JsonResponse
from django.test import override_settings

import sirenity
from sirenity import (
    SirenMcpExecution,
    SirenMcpOperation,
    SirenMiddleware,
    siren_configuration,
    siren_mcp,
)

example_schema = {
    "openapi": "3.1.1",
    "info": {"title": "Example consumer", "version": "example-1"},
    "paths": {
        "/example_resources": {
            "get": {
                "operationId": "list_example_resources",
                "summary": "List example resources",
                "description": "List example resources.",
                "responses": {"200": {"description": "Example response"}},
            }
        }
    },
}
example_openapi_calls = 0


def example_openapi():
    global example_openapi_calls
    example_openapi_calls += 1
    return example_schema


class ExampleExecutor:
    def execute(self, example_operation: SirenMcpOperation) -> SirenMcpExecution:
        raise AssertionError("example executor should not run")


if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8")
example_configuration = siren_configuration(
    openapi="wheel_example_django_mcp_consumer.example_openapi",
    policy="sirenity.SirenAllowAllPolicy",
)
with override_settings(SIRENITY=example_configuration):
    example_django = SirenMiddleware(
        lambda example_request: JsonResponse({"example_result": "example-django"})
    )
example_mcp = siren_mcp(example_configuration, executor=ExampleExecutor())

assert example_django.middleware.adapter is example_configuration.adapter()
assert example_mcp.adapter is example_configuration.adapter()
assert example_openapi_calls == 1
print(sirenity.__file__)
