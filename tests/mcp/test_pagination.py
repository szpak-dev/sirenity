from sirenity.api import SirenMcpExecution, SirenMcpInvocation, siren_configuration, siren_mcp

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor


class TestMcpPaginationAttacks(McpCase):
    def test_adversarial_missing_required_argument_does_not_execute(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={},
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

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="get_example_record",
                arguments={},
            )
        )

        assert result.is_error is True
        assert executor.calls == []

    def test_invariant_invalid_runtime_has_more_executes_once(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": "yes",
                        "next_example_offset": 2,
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

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="list_example_records",
                arguments={"example_filter": "example-open"},
            )
        )

        assert result.is_error is True
        assert result.structured_content == {"detail": "Siren continuation has_more value must be boolean"}
        assert len(executor.calls) == 1

    def test_cleanup_invalid_result_exposes_no_partial_continuation(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": True,
                        "next_example_offset": None,
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

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="list_example_records",
                arguments={"example_filter": "example-open"},
            )
        )

        assert result.is_error is True
        assert result.continuations == ()

    def test_recovery_uses_the_next_executor_result_after_an_invalid_result(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": "yes",
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
                        "next_example_offset": 2,
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
        invocation = SirenMcpInvocation(
            operation_id="list_example_records",
            arguments={"example_filter": "example-open"},
        )

        failed = bridge.invoke(invocation)
        recovered = bridge.invoke(invocation)

        assert failed.is_error is True
        assert recovered.is_error is False
        assert recovered.continuations == ()
        assert len(executor.calls) == 2


class TestMcpPaginationHappyPaths(McpCase):
    def test_typed_pagination_invocation_can_be_followed_directly(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": True,
                        "next_example_offset": 2,
                        "example_limit": 2,
                        "example_revision": "example-revision-2",
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
                        "example_revision": "example-revision-2",
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
                arguments={
                    "example_filter": "example-open",
                    "example_offset": 0,
                    "example_limit": 99,
                    "example_revision": "example-stale",
                    "example_noise": "example-excluded",
                },
            )
        )
        second = bridge.invoke(first.continuations[0])

        assert first.continuations[0] == SirenMcpInvocation(
            operation_id="list_example_records",
            arguments={
                "example_filter": "example-open",
                "example_offset": 2,
                "example_limit": 2,
                "example_revision": "example-revision-2",
            },
        )
        assert second.continuations == ()
        assert len(executor.calls) == 2

    def test_incomplete_page_exposes_matching_siren_and_mcp_targets(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": True,
                        "next_example_offset": 2,
                        "example_limit": 2,
                        "example_revision": "example-revision-2",
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

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="list_example_records",
                arguments={"example_filter": "example-open"},
            )
        )

        assert result.structured_content["links"][-1]["rel"] == ["next"]
        assert result.continuations[0] == SirenMcpInvocation(
            operation_id="list_example_records",
            arguments={
                "example_filter": "example-open",
                "example_offset": 2,
                "example_limit": 2,
                "example_revision": "example-revision-2",
            },
        )
        assert result.structured_content["links"][-1]["href"] == (
            "https://api.example.test/siren/example_records?example_filter=example-open"
            "&example_offset=2&example_limit=2&example_revision=example-revision-2"
        )

    def test_final_page_exposes_no_typed_continuation(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "example_items": [],
                        "has_more": False,
                        "next_example_offset": 2,
                        "example_limit": 2,
                        "example_revision": "example-revision-2",
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

        result = bridge.invoke(
            SirenMcpInvocation(
                operation_id="list_example_records",
                arguments={"example_filter": "example-open"},
            )
        )

        assert result.is_error is False
        assert result.continuations == ()
