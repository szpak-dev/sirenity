import pytest

from sirenity.api import (
    SirenityError,
    SirenMcpExecution,
    SirenMcpInvocation,
    siren_configuration,
    siren_mcp,
)

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor


class TestMcpInvocationAttacks(McpCase):
    def test_adversarial_unknown_operation_is_rejected_before_execution(self) -> None:
        executor = ExampleExecutor((SirenMcpExecution(status=200, result={}, base_url="https://api.example.test"),))
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(SirenMcpInvocation(operation_id="example-missing", arguments={}))

        assert result.is_error is True
        assert executor.calls == []

    def test_adversarial_missing_required_inputs_are_rejected_before_execution(self) -> None:
        executor = ExampleExecutor((SirenMcpExecution(status=200, result={}, base_url="https://api.example.test"),))
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="update_example_record",
                arguments={"example_record_id": "example-record-1"},
            )
        )

        assert result.is_error is True
        assert executor.calls == []

    def test_adversarial_unknown_input_is_rejected_at_the_public_operation_boundary(self) -> None:
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=ExampleExecutor((SirenMcpExecution(status=200, result={}, base_url="https://api.example.test"),)),
        )

        with pytest.raises(SirenityError, match="unknown arguments"):
            bridge.operation(
                SirenMcpInvocation(
                    operation_id="update_example_record",
                    arguments={
                        "example_record_id": "example-record-1",
                        "example_title": "Example title",
                        "example_metadata": {"example_source": "example"},
                        "example_trace": "example-trace-1",
                        "example_unknown": "example-unknown",
                    },
                )
            )

    def test_invariant_invalid_schema_value_is_rejected_before_execution(self) -> None:
        executor = ExampleExecutor((SirenMcpExecution(status=200, result={}, base_url="https://api.example.test"),))
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="update_example_record",
                arguments={
                    "example_record_id": "example-record-1",
                    "example_title": "Example title",
                    "example_metadata": "example-invalid",
                    "example_trace": "example-trace-1",
                },
            )
        )

        assert result.is_error is True
        assert executor.calls == []

    def test_cleanup_invalid_invocation_exposes_only_the_public_error_shape(self) -> None:
        executor = ExampleExecutor((SirenMcpExecution(status=200, result={}, base_url="https://api.example.test"),))
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(SirenMcpInvocation(operation_id="update_example_record", arguments={}))

        assert result.structured_content == {"detail": "Siren MCP invocation is invalid"}
        assert result.continuations == ()

    def test_recovery_valid_invocation_succeeds_after_invalid_input(self) -> None:
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
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=executor,
        )

        failed = bridge.invoke(SirenMcpInvocation(operation_id="update_example_record", arguments={}))
        recovered = bridge.invoke(
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

        assert failed.is_error is True
        assert recovered.is_error is False
        assert len(executor.calls) == 1


class TestMcpInvocationHappyPaths(McpCase):
    def test_compiled_inputs_are_separated_for_caller_execution(self) -> None:
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
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="update_example_record",
                arguments={
                    "example_record_id": "example/record 1",
                    "example_title": "Example updated",
                    "example_metadata": {"example_source": "example"},
                    "example_page": 2,
                    "example_trace": "example-trace-1",
                    "example_session": "example-session-1",
                },
            )
        )

        operation = executor.calls[0]
        assert operation.operation_id == "update_example_record"
        assert operation.method == "PATCH"
        assert operation.dispatch_path == "/api/example_records/example%2Frecord%201"
        assert operation.path_values == {"example_record_id": "example/record 1"}
        assert operation.body == {
            "example_title": "Example updated",
            "example_metadata": {"example_source": "example"},
        }
        assert operation.query_values == {"example_page": 2}
        assert operation.header_values == {"example_trace": "example-trace-1"}
        assert operation.cookie_values == {"example_session": "example-session-1"}
        assert result.is_error is False

    def test_tool_exposes_the_caller_visible_operation_contract(self) -> None:
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
            ),
            executor=ExampleExecutor((SirenMcpExecution(status=200, result={}, base_url="https://api.example.test"),)),
        )

        tool = bridge.tools()[0]

        assert tool.name == "update_example_record"
        assert tool.title == "Update example record"
        assert tool.description == "Update one example record."
        assert tool.input_schema["required"] == [
            "example_metadata",
            "example_record_id",
            "example_title",
            "example_trace",
        ]

    def test_valid_invocation_executes_exactly_once(self) -> None:
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
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
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

        assert len(executor.calls) == 1
        assert result.structured_content["properties"]["example_title"] == "Example updated"
        assert result.verifications == ()
