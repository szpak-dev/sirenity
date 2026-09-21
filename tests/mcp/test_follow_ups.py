from sirenity.api import SirenMcpExecution, SirenMcpInvocation, siren_configuration, siren_mcp

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor


class TestMcpFollowUpAttacks(McpCase):
    def test_adversarial_unauthorized_read_is_not_exposed_as_a_typed_follow_up(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_dashboard_id": "example-dashboard-1",
                        "primary_record_id": "example-record-1",
                        "secondary_record_id": "example-record-2",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_SINGLE_FOLLOW_UP_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.follow_up_policy.ExampleDashboardOnlyPolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_dashboard",
                arguments={"example_dashboard_id": "example-dashboard-1"},
            )
        )

        assert result.is_error is False
        assert result.follow_ups == ()
        assert result.structured_content["links"][-1]["rel"] == ["item"]

    def test_invariant_required_header_suppresses_an_unexecutable_follow_up(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_dashboard_id": "example-dashboard-1",
                        "primary_record_id": "example-record-1",
                        "secondary_record_id": "example-record-2",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_UNSUPPORTED_FOLLOW_UP_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.follow_up_policy.ExampleFollowUpPolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_dashboard",
                arguments={"example_dashboard_id": "example-dashboard-1"},
            )
        )

        assert result.is_error is False
        assert result.follow_ups == ()
        assert result.structured_content["links"][-1]["rel"] == ["item"]


class TestMcpFollowUpHappyPaths(McpCase):
    def test_required_query_argument_is_derived_from_the_response_link(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_dashboard_id": "example-dashboard-1",
                        "primary_record_id": "example-record-1",
                        "secondary_record_id": "example-record-2",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_REQUIRED_QUERY_FOLLOW_UP_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.follow_up_policy.ExampleFollowUpPolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_dashboard",
                arguments={"example_dashboard_id": "example-dashboard-1"},
            )
        )

        assert result.follow_ups == (
            SirenMcpInvocation(
                operation_id="get_example_record",
                arguments={
                    "example_record_id": "example-record-1",
                    "example_locale": "example-dashboard-1",
                },
            ),
        )

    def test_read_exposes_multiple_follow_ups_separately_from_other_navigation(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_dashboard_id": "example-dashboard-1",
                        "primary_record_id": "example-record-1",
                        "secondary_record_id": "example-record-2",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_FOLLOW_UPS_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.follow_up_policy.ExampleFollowUpPolicy",
            ),
            executor=executor,
        )

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_dashboard",
                arguments={"example_dashboard_id": "example-dashboard-1"},
            )
        )

        assert result.continuations == ()
        assert result.verifications == ()
        assert result.follow_ups == (
            SirenMcpInvocation(
                operation_id="get_example_record",
                arguments={"example_record_id": "example-record-1"},
            ),
            SirenMcpInvocation(
                operation_id="get_example_record",
                arguments={"example_record_id": "example-record-2"},
            ),
        )
        assert "example_locale" not in result.follow_ups[0].arguments

    def test_single_follow_up_can_be_invoked_directly(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_dashboard_id": "example-dashboard-1",
                        "primary_record_id": "example-record-1",
                        "secondary_record_id": "example-record-2",
                    },
                    base_url="https://api.example.test",
                ),
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_record_id": "example-record-1",
                        "example_title": "Example record",
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_SINGLE_FOLLOW_UP_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.follow_up_policy.ExampleFollowUpPolicy",
            ),
            executor=executor,
        )

        source = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_dashboard",
                arguments={"example_dashboard_id": "example-dashboard-1"},
            )
        )
        followed = bridge.invoke(source.follow_ups[0])

        assert followed.is_error is False
        assert followed.follow_ups == ()
        assert executor.calls[1].operation_id == "get_example_record"
        assert executor.calls[1].dispatch_path == "/api/example_records/example-record-1"
        assert executor.calls[1].query_values == {}
