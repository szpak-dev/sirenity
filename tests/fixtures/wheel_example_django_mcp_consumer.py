import json

from django.conf import settings
from django.http import JsonResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path

if not settings.configured:
    settings.configure(
        ALLOWED_HOSTS=["testserver"],
        DEFAULT_CHARSET="utf-8",
        ROOT_URLCONF=__name__,
    )

from ninja import NinjaAPI, Schema

import sirenity
from sirenity import (
    SirenMcpExecution,
    SirenMcpOperation,
    SirenMiddleware,
    siren_configuration,
    siren_mcp,
)


class ExampleUpdateResourcePayload(Schema):
    title: str


class ExampleResource(Schema):
    example_resource_id: str
    title: str


class ExampleGroup(Schema):
    id: str
    title: str


class ExampleItem(Schema):
    id: str
    example_group_id: str
    title: str


example_application_calls = 0
example_api = NinjaAPI(title="Example consumer", version="example-1", urls_namespace="example_issue_199")


@example_api.patch(
    "/api/example_resources/{example_resource_id}",
    description="Update an example resource.",
    operation_id="update_example_resource",
    response=ExampleResource,
    summary="Update example resource",
)
def example_update_resource(
    request,
    example_resource_id: str,
    payload: ExampleUpdateResourcePayload,
):
    global example_application_calls
    example_application_calls += 1
    return {
        "example_resource_id": example_resource_id,
        "title": payload.title,
    }


@example_api.get(
    "/api/example_groups/{example_group_id}",
    description="Read an example group.",
    operation_id="get_example_group",
    response=ExampleGroup,
    summary="Read example group",
)
def example_get_group(request, example_group_id: str):
    return {
        "id": example_group_id,
        "title": "Example group",
    }


@example_api.get(
    "/api/example_groups/{example_group_id}/example_items",
    description="List example items in an example group.",
    operation_id="list_example_group_items",
    response=list[ExampleItem],
    summary="List example group items",
)
def example_list_group_items(request, example_group_id: str):
    return [{"id": "example-item-42", "example_group_id": example_group_id, "title": "Example item"}]


@example_api.get(
    "/api/example_groups/{example_group_id}/example_items/{example_item_id}",
    description="Read an example item in an example group.",
    operation_id="get_example_group_item",
    response=ExampleItem,
    summary="Read example group item",
)
def example_get_group_item(request, example_group_id: str, example_item_id: str):
    return {"id": example_item_id, "example_group_id": example_group_id, "title": "Example item"}


urlpatterns = [path("", example_api.urls)]


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


example_configuration = siren_configuration(
    openapi="wheel_example_django_mcp_consumer.example_api",
    source_path="/api",
    public_path="/siren",
    policy="sirenity.SirenAllowAllPolicy",
)


def example_response(example_request):
    if example_request.path.endswith("/example_items"):
        return JsonResponse(
            [{
                "id": "example-item-42",
                "example_group_id": "example-group-42",
                "title": "Example item",
            }],
            safe=False,
        )
    return JsonResponse({
        "id": "example-group-42",
        "title": "Example group",
    })


with override_settings(SIRENITY=example_configuration):
    example_django = SirenMiddleware(example_response)
    example_group_response = example_django(
        RequestFactory().get(
            "/siren/example_groups/example-group-42",
            HTTP_ACCEPT="application/vnd.siren+json",
        )
    )
    example_items_response = example_django(
        RequestFactory().get(
            "/siren/example_groups/example-group-42/example_items",
            HTTP_ACCEPT="application/vnd.siren+json",
        )
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
assert example_result.is_error is False, example_result.structured_content
assert example_application_calls == 1
assert json.loads(example_group_response.content)["links"] == [
    {
        "title": "ExampleGroup",
        "rel": ["self"],
        "href": "http://testserver/siren/example_groups/example-group-42",
    },
    {
        "title": "ExampleItem",
        "rel": ["collection"],
        "href": "http://testserver/siren/example_groups/example-group-42/example_items",
    },
]
assert json.loads(example_items_response.content)["entities"][0]["links"] == [{
    "title": "Example item",
    "rel": ["self"],
    "href": "http://testserver/siren/example_groups/example-group-42/example_items/example-item-42",
}]
assert example_result.structured_content["properties"] == {
    "example_resource_id": "example-resource-42",
    "title": "Updated example resource",
}
print(sirenity.__file__)
