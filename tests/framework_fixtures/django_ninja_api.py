from ninja import NinjaAPI, Schema


class ExampleResource(Schema):
    example_resource_id: str
    title: str


class ExampleGroup(Schema):
    example_group_id: str
    title: str


django_ninja_api = NinjaAPI(title="Example API", version="1", urls_namespace="sirenity_issue_199")


@django_ninja_api.get(
    "/api/example_resources",
    description="List example resources.",
    operation_id="list_example_resources",
    response=list[ExampleResource],
    summary="List example resources",
)
def list_example_resources(request):
    return []


@django_ninja_api.get(
    "/api/example_groups/{example_group_id}",
    description="Read an example group.",
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
    operation_id="get_example_group",
    response=ExampleGroup,
    summary="Read example group",
)
def get_example_group(request, example_group_id: str):
    return {"example_group_id": example_group_id, "title": "Example group"}


@django_ninja_api.get(
    "/api/example_groups/{example_group_id}/example_resources",
    description="List example resources in an example group.",
    operation_id="list_example_group_resources",
    response=list[ExampleResource],
    summary="List example group resources",
)
def list_example_group_resources(request, example_group_id: str):
    return []
