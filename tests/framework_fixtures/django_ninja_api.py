from ninja import NinjaAPI, Schema


class ExampleResource(Schema):
    example_resource_id: str
    title: str


django_ninja_api = NinjaAPI(title="Example API", version="1", urls_namespace="sirenity_issue_195")


@django_ninja_api.get(
    "/api/example_resources",
    description="List example resources.",
    operation_id="list_example_resources",
    response=list[ExampleResource],
    summary="List example resources",
)
def list_example_resources(request):
    return []
