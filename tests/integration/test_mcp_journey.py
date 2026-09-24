import pytest

from sirenity.api import SirenMcpExecution, SirenMcpInvocation, siren_configuration, siren_mcp

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor, ExampleInterruptedExecutor


class TestMcpJourneyAttacks(McpCase):
    def test_adversarial_interrupted_execution_is_not_retried(self) -> None:
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

    def test_recovery_same_bridge_invokes_after_interruption(self) -> None:
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


class TestMcpJourneyHappyPaths(McpCase):
    def test_configuration_executor_and_typed_bounded_target_form_one_flow(self) -> None:
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
                    "example_source_only": "example-source-only",
                },
            )
        )
        final = bridge.invoke(first.continuations[0])

        assert first.continuations[0].operation_id == "get_example_job_output"
        assert "example_source_only" not in first.continuations[0].arguments
        assert final.structured_content["properties"] == {"example_output_id": "example-output-2"}
        assert len(executor.calls) == 2

    def test_configuration_executor_and_typed_pagination_form_one_flow(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": True,
                        "next_example_offset": 2,
                        "example_limit": 2,
                        "example_revision": "example-revision-1",
                    },
                    base_url="https://api.example.test",
                ),
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": False,
                        "next_example_offset": 4,
                        "example_limit": 2,
                        "example_revision": "example-revision-1",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_PAGINATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        first = bridge.invoke(
            SirenMcpInvocation(
                operation_id="list_example_records",
                arguments={"example_filter": "example-open"},
            )
        )
        final = bridge.invoke(first.continuations[0])

        assert first.structured_content["links"][-1]["rel"] == ["next"]
        assert final.continuations == ()
        assert len(executor.calls) == 2
