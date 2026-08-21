import json

from django.conf import settings
from django.http import JsonResponse
from django.test import Client, override_settings
from django.urls import path

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
        "/api/example_resources/{example_resource_id}": {
            "parameters": [{
                "name": "example_resource_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }],
            "patch": {
                "operationId": "update_example_resource",
                "summary": "Update example resource",
                "description": "Update one example resource.",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {
                        "type": "object",
                        "required": ["title"],
                        "properties": {"title": {"type": "string", "title": "Title"}},
                    }}},
                },
                "responses": {"200": {
                    "description": "Updated example resource.",
                    "content": {"application/json": {"schema": {
                        "type": "object",
                        "title": "Example resource",
                        "properties": {
                            "example_resource_id": {"type": "string"},
                            "title": {"type": "string"},
                        },
                    }}},
                }},
            }
        }
    },
}
example_openapi_calls = 0
example_application_calls = 0


def example_openapi():
    global example_openapi_calls
    example_openapi_calls += 1
    return example_schema


class ExampleExecutor:
    def execute(self, example_operation: SirenMcpOperation) -> SirenMcpExecution:
        example_response = Client().generic(
            example_operation.method,
            example_operation.dispatch_path,
            data=json.dumps(example_operation.body),
            content_type="application/json",
        )
        return SirenMcpExecution(
            status=example_response.status_code,
            result=example_response.json(),
            base_url="http://testserver",
            request_url=f"http://testserver{example_operation.dispatch_path}",
            headers=dict(example_response.headers),
        )


def example_update_resource(example_request, example_resource_id):
    global example_application_calls
    example_application_calls += 1
    example_body = json.loads(example_request.body)
    return JsonResponse({
        "example_resource_id": example_resource_id,
        "title": example_body["title"],
    })


urlpatterns = [
    path("api/example_resources/<str:example_resource_id>", example_update_resource),
]


if not settings.configured:
    settings.configure(
        ALLOWED_HOSTS=["testserver"],
        DEFAULT_CHARSET="utf-8",
        ROOT_URLCONF=__name__,
    )
example_configuration = siren_configuration(
    openapi="wheel_example_django_mcp_consumer.example_openapi",
    source_path="/api",
    public_path="/siren",
    policy="sirenity.SirenAllowAllPolicy",
)
with override_settings(SIRENITY=example_configuration):
    example_django = SirenMiddleware(
        lambda example_request: JsonResponse({"example_result": "example-django"})
    )
example_mcp = siren_mcp(example_configuration, executor=ExampleExecutor())
example_result = example_mcp.invoke(sirenity.SirenMcpInvocation(
    operation_id="update_example_resource",
    arguments={
        "example_resource_id": "example-resource-42",
        "title": "Updated example resource",
    },
))

assert example_django.middleware.adapter is example_configuration.adapter()
assert example_mcp.adapter is example_configuration.adapter()
assert example_openapi_calls == 1
assert example_application_calls == 1
assert example_result.is_error is False
assert example_result.structured_content["properties"] == {
    "example_resource_id": "example-resource-42",
    "title": "Updated example resource",
}
print(sirenity.__file__)
