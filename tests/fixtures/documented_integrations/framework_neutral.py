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
