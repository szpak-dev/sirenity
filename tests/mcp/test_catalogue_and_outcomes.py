import pytest

from sirenity.api import (
    SirenMcpExecution,
    SirenMcpInvocation,
    siren_configuration,
    siren_mcp,
)

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor, ExampleInterruptedExecutor


class TestMcpCatalogueAndOutcomeAttacks(McpCase):
    def test_adversarial_application_error_is_returned_as_an_mcp_error(self) -> None:
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=ExampleExecutor(
                (
                    SirenMcpExecution(
                        status=503,
                        result={"example_detail": "example unavailable"},
                        base_url="https://api.example.test",
                    ),
                )
            ),
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={"example_job_id": "example-job-1"},
            )
        )

        assert result.is_error is True
        assert result.structured_content["properties"] == {
            "example_detail": "example unavailable",
            "status": 503,
        }
        assert result.continuations == ()

    def test_invariant_invalid_success_result_becomes_a_public_mcp_error(self) -> None:
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=ExampleExecutor(
                (
                    SirenMcpExecution(
                        status=200,
                        result=[],
                        base_url="https://api.example.test",
                    ),
                )
            ),
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_job",
                arguments={"example_job_id": "example-job-1"},
            )
        )

        assert result.is_error is True
        assert result.structured_content == {"detail": "OpenAPI object response requires a mapping result"}

    def test_interrupted_executor_is_not_hidden_or_retried(self) -> None:
        executor = ExampleInterruptedExecutor(
            SirenMcpExecution(status=503, result={}, base_url="https://api.example.test")
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        with pytest.raises(RuntimeError, match="example execution interrupted"):
            bridge.invoke(
                SirenMcpInvocation(
                    operation_id="get_example_job",
                    arguments={"example_job_id": "example-job-1"},
                )
            )

        assert len(executor.calls) == 1

    def test_recovery_same_catalogue_remains_usable_after_interruption(self) -> None:
        executor = ExampleInterruptedExecutor(
            SirenMcpExecution(
                status=200,
                result={"example_job_id": "example-job-1", "example_state": "complete"},
                base_url="https://api.example.test",
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
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
        assert recovered.structured_content["properties"]["example_state"] == "complete"
        assert [tool.name for tool in bridge.tools()] == ["get_example_job"]


class TestMcpCatalogueAndOutcomeHappyPaths(McpCase):
    def test_equivalent_configurations_have_the_same_catalogue_fingerprint(self) -> None:
        first = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                policy="tests.support.collaborators.ExamplePolicy",
                source_path="/",
                public_path="/",
                profiles=(),
            ),
            executor=ExampleExecutor(()),
        )
        second = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                policy="tests.support.collaborators.ExamplePolicy",
                source_path="/",
                public_path="/",
                profiles=(),
            ),
            executor=ExampleExecutor(()),
        )

        assert first.catalogue_fingerprint == second.catalogue_fingerprint
        assert len(first.catalogue_fingerprint) == 64

    def test_changed_operation_contract_changes_the_catalogue_fingerprint(self) -> None:
        entity = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
                policy="tests.support.collaborators.ExamplePolicy",
                source_path="/",
                public_path="/",
                profiles=(),
            ),
            executor=ExampleExecutor(()),
        )
        operation = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_OPERATION_OPENAPI",
                policy="tests.support.collaborators.ExamplePolicy",
                source_path="/",
                public_path="/",
                profiles=(),
            ),
            executor=ExampleExecutor(()),
        )

        assert entity.catalogue_fingerprint != operation.catalogue_fingerprint

    def test_tools_are_deterministic_caller_registration_values(self) -> None:
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_PAGINATION_OPENAPI",
                policy="tests.support.collaborators.ExamplePolicy",
                source_path="/",
                public_path="/",
                profiles=(),
            ),
            executor=ExampleExecutor(()),
        )

        first = bridge.tools()
        second = bridge.tools()

        assert [tool.name for tool in first] == [
            "get_example_record",
            "list_example_records",
        ]
        assert first == second

    def test_successful_execution_projects_an_mcp_document(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={"example_job_id": "example-job-1", "example_state": "complete"},
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ENTITY_OPENAPI",
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
        assert result.structured_content["class"] == ["example-job"]
        assert len(executor.calls) == 1
