from example_project.application import example_get_response
from example_project.execution import ExampleMcpExecutor

from sirenity import SirenMcpInvocation, siren_configuration, siren_mcp

example_configuration = siren_configuration(
    openapi="example_project.api.openapi_schema",
    source_path="/api",
    public_path="/siren",
    policy="example_project.permissions.siren_policy",
    profiles=("sirenity.SirenStructuredFormProfile",),
)
example_django = example_configuration.django(example_get_response)
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
