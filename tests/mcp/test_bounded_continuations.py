import pytest

from sirenity.api import SirenMcpExecution, SirenMcpInvocation, siren_configuration, siren_mcp

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor, ExampleInterruptedExecutor


class TestMcpBoundedContinuationAttacks(McpCase):
    def test_adversarial_invalid_invocation_does_not_execute_application_code(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={"example_state": "unused"},
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        result = bridge.invoke(SirenMcpInvocation(operation_id="get_missing_example_job", arguments={}))

        assert result.is_error is True
        assert result.structured_content == {"detail": "Siren MCP invocation is invalid"}
        assert executor.calls == []

    def test_invariant_runtime_null_continuation_executes_once_and_returns_one_error(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "running",
                        "has_more": True,
                        "next_example_cursor": None,
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={"example_job_id": "example-job-1"},
            )
        )

        assert result.is_error is True
        assert result.structured_content == {"detail": "Siren continuation values cannot be null"}
        assert result.continuations == ()
        assert len(executor.calls) == 1

    def test_interruption_does_not_retry_the_executor(self) -> None:
        executor = ExampleInterruptedExecutor(
            SirenMcpExecution(
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                },
                base_url="https://api.example.test",
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )
        invocation = SirenMcpInvocation(
            operation_id="get_example_job",
            arguments={"example_job_id": "example-job-1"},
        )

        with pytest.raises(RuntimeError, match="example execution interrupted"):
            bridge.invoke(invocation)

        assert len(executor.calls) == 1

    def test_cleanup_after_interruption_does_not_create_a_continuation(self) -> None:
        executor = ExampleInterruptedExecutor(
            SirenMcpExecution(
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                },
                base_url="https://api.example.test",
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )
        invocation = SirenMcpInvocation(
            operation_id="get_example_job",
            arguments={"example_job_id": "example-job-1"},
        )

        with pytest.raises(RuntimeError):
            bridge.invoke(invocation)
        recovered = bridge.invoke(invocation)

        assert recovered.is_error is False
        assert recovered.continuations == ()
        assert len(executor.calls) == 2

    def test_recovery_accepts_a_valid_invocation_after_an_invalid_invocation(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "complete",
                        "has_more": False,
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        failed = bridge.invoke(SirenMcpInvocation(operation_id="example-missing", arguments={}))
        recovered = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={"example_job_id": "example-job-1"},
            )
        )

        assert failed.is_error is True
        assert recovered.is_error is False
        assert len(executor.calls) == 1


class TestMcpBoundedContinuationHappyPaths(McpCase):
    def test_cross_operation_typed_continuation_drops_source_only_arguments(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "running",
                        "has_more": True,
                        "next_example_cursor": "example-cursor-2",
                        "next_example_output_id": "example-output-2",
                        "next_example_locale": "example-en",
                    },
                    base_url="https://api.example.test",
                ),
                SirenMcpExecution(
                    status=200,
                    result={"example_output_id": "example-output-2"},
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi=("tests.support.applications.configuration.EXAMPLE_CROSS_OPERATION_BOUNDED_OPENAPI"),
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        first = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={
                    "example_job_id": "example-job-1",
                    "example_filter": "example-open",
                    "example_cursor": "example-cursor-1",
                    "example_source_only": "example-source-only",
                },
            )
        )
        second = bridge.invoke(first.continuations[0])

        assert first.continuations[0] == SirenMcpInvocation(
            operation_id="get_example_job_output",
            arguments={
                "example_job_id": "example-job-1",
                "example_output_id": "example-output-2",
                "example_filter": "example-open",
                "example_locale": "example-en",
            },
        )
        assert second.is_error is False
        assert second.structured_content["properties"] == {"example_output_id": "example-output-2"}
        assert len(executor.calls) == 2

    def test_typed_continuation_can_be_invoked_directly_until_completion(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "running",
                        "has_more": True,
                        "next_example_cursor": "example-cursor-2",
                    },
                    base_url="https://api.example.test",
                ),
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "complete",
                        "has_more": False,
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        first = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={
                    "example_job_id": "example-job-1",
                    "example_filter": "example-open",
                    "example_cursor": "example-cursor-1",
                },
            )
        )
        second = bridge.invoke(first.continuations[0])

        assert first.is_error is False
        assert first.continuations == (
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={
                    "example_job_id": "example-job-1",
                    "example_filter": "example-open",
                    "example_cursor": "example-cursor-2",
                },
            ),
        )
        assert second.is_error is False
        assert second.continuations == ()
        assert len(executor.calls) == 2

    def test_executor_receives_encoded_path_and_separated_query_values(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_job_id": "example/job 1",
                        "example_state": "complete",
                        "has_more": False,
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={
                    "example_job_id": "example/job 1",
                    "example_filter": "example-open",
                },
            )
        )

        assert executor.calls[0].method == "GET"
        assert executor.calls[0].dispatch_path == "/api/example_jobs/example%2Fjob%201"
        assert executor.calls[0].path_values == {"example_job_id": "example/job 1"}
        assert executor.calls[0].query_values == {"example_filter": "example-open"}

    def test_final_result_has_zero_typed_continuations(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "complete",
                        "has_more": False,
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={"example_job_id": "example-job-1"},
            )
        )

        assert result.is_error is False
        assert result.continuations == ()
        assert len(executor.calls) == 1
