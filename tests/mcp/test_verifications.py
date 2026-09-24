from sirenity.api import SirenMcpExecution, SirenMcpInvocation, siren_configuration, siren_mcp

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor


class TestMcpVerificationAttacks(McpCase):
    def test_unauthorized_canonical_read_suppresses_the_verification(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_record_id": "example-record-1",
                        "example_title": "Example created",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_CREATION_VERIFICATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExampleMutationOnlyPolicy",
                profiles=(),
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="create_example_record",
                arguments={
                    "example_title": "Example created",
                    "example_metadata": {"example_source": "example"},
                    "example_trace": "example-trace-1",
                },
            )
        )

        assert result.is_error is False
        assert result.continuations == ()
        assert result.verifications == ()
        assert len(executor.calls) == 1

    def test_required_header_suppresses_the_verification(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_record_id": "example-record-1",
                        "example_title": "Example updated",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_UNSUPPORTED_VERIFICATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="update_example_record",
                arguments={
                    "example_record_id": "example-record-1",
                    "example_title": "Example updated",
                    "example_metadata": {"example_source": "example"},
                    "example_trace": "example-trace-1",
                },
            )
        )

        assert result.is_error is False
        assert result.continuations == ()
        assert result.verifications == ()
        assert len(executor.calls) == 1


class TestMcpVerificationHappyPaths(McpCase):
    def test_creation_derives_canonical_verification_without_response_link(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_record_id": "example-record-1",
                        "example_title": "Example created",
                    },
                    base_url="https://api.example.test",
                ),
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_record_id": "example-record-1",
                        "example_title": "Example created",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_CREATION_VERIFICATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        creation = bridge.invoke(
            SirenMcpInvocation(
                operation_id="create_example_record",
                arguments={
                    "example_title": "Example created",
                    "example_metadata": {"example_source": "example"},
                    "example_trace": "example-trace-1",
                },
            )
        )
        verification = bridge.invoke(creation.verifications[0])

        assert creation.continuations == ()
        assert creation.verifications == (
            SirenMcpInvocation(
                operation_id="get_example_record",
                arguments={"example_record_id": "example-record-1"},
            ),
        )
        assert verification.is_error is False
        assert verification.continuations == ()
        assert verification.verifications == ()
        assert executor.calls[1].method == "GET"
        assert executor.calls[1].dispatch_path == "/api/example_records/example-record-1"
        assert executor.calls[1].path_values == {"example_record_id": "example-record-1"}

    def test_mutation_exposes_a_separate_invokable_verification(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_record_id": "example-record-1",
                        "example_title": "Example updated",
                    },
                    base_url="https://api.example.test",
                ),
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_record_id": "example-record-1",
                        "example_title": "Example updated",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_VERIFICATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        mutation = bridge.invoke(
            SirenMcpInvocation(
                operation_id="update_example_record",
                arguments={
                    "example_record_id": "example-record-1",
                    "example_title": "Example updated",
                    "example_metadata": {"example_source": "example"},
                    "example_trace": "example-trace-1",
                },
            )
        )
        verification = bridge.invoke(mutation.verifications[0])

        assert mutation.continuations == ()
        assert mutation.verifications == (
            SirenMcpInvocation(
                operation_id="get_example_record",
                arguments={"example_record_id": "example-record-1"},
            ),
        )
        assert verification.is_error is False
        assert verification.continuations == ()
        assert verification.verifications == ()
        assert executor.calls[1].method == "GET"
        assert executor.calls[1].dispatch_path == "/api/example_records/example-record-1"
        assert executor.calls[1].path_values == {"example_record_id": "example-record-1"}
