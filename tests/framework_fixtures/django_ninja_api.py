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


@django_ninja_api.post(
    "/api/example_groups",
    description="Create an example group.",
    operation_id="create_example_group",
    response={201: ExampleGroup},
    summary="Create example group",
)
def create_example_group(request):
    return 201, {"example_group_id": "created-example-group", "title": "Created example group"}


@django_ninja_api.get(
    "/api/example_groups/{example_group_id}",
    description="Read an example group.",
    operation_id="get_example_group",
    response=ExampleGroup,
    summary="Read example group",
)
def get_example_group(request, example_group_id: str):
    return {"example_group_id": example_group_id, "title": "Example group"}


@django_ninja_api.patch(
    "/api/example_groups/{example_group_id}",
    description="Update an example group.",
    operation_id="update_example_group",
    response=ExampleGroup,
    summary="Update example group",
)
def update_example_group(request, example_group_id: str):
    return {"example_group_id": example_group_id, "title": "Updated example group"}


@django_ninja_api.get(
    "/api/example_groups/{example_group_id}/example_resources",
    description="List example resources in an example group.",
    operation_id="list_example_group_resources",
    response=list[ExampleResource],
    summary="List example group resources",
)
def list_example_group_resources(request, example_group_id: str):
    return []
