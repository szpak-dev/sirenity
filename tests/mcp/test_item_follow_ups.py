from sirenity.api import SirenMcpExecution, SirenMcpInvocation, siren_configuration, siren_mcp

from ..cases import McpCase
from ..support.collaborators import ExampleExecutor


class TestMcpItemFollowUpHappyPaths(McpCase):
    def test_multiple_item_follow_ups_coexist_with_next_and_one_survives_on_the_terminal_page(self) -> None:
        executor = ExampleExecutor(
            (
                SirenMcpExecution(
                    status=200,
                    result={
                        "items": [
                            {"item_id": "item-1", "expected_revision": "revision-1"},
                            {"item_id": "item-2", "expected_revision": "revision-2"},
                        ],
                        "has_more": True,
                        "next_offset": 2,
                        "limit": 2,
                    },
                    base_url="https://api.example.test",
                ),
                SirenMcpExecution(
                    status=200,
                    result={
                        "items": [{"item_id": "item-3", "expected_revision": "revision-3"}],
                        "has_more": False,
                        "next_offset": 3,
                        "limit": 2,
                    },
                    base_url="https://api.example.test",
                ),
            )
        )
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ITEM_FOLLOW_UPS_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=executor,
        )

        first = bridge.invoke(SirenMcpInvocation(operation_id="list_example_items", arguments={}))
        second = bridge.invoke(first.continuations[0])

        assert first.follow_ups == (
            SirenMcpInvocation(
                operation_id="read_example_item_content",
                arguments={"item_id": "item-1", "expected_revision": "revision-1"},
            ),
            SirenMcpInvocation(
                operation_id="read_example_item_content",
                arguments={"item_id": "item-2", "expected_revision": "revision-2"},
            ),
        )
        assert [entity["links"][-1]["href"] for entity in first.structured_content["entities"]] == [
            "https://api.example.test/siren/example_items/item-1?expected_revision=revision-1",
            "https://api.example.test/siren/example_items/item-2?expected_revision=revision-2",
        ]
        assert all(entity["links"][-1]["rel"] == ["item"] for entity in first.structured_content["entities"])
        assert len(first.continuations) == 1
        assert second.follow_ups == (
            SirenMcpInvocation(
                operation_id="read_example_item_content",
                arguments={"item_id": "item-3", "expected_revision": "revision-3"},
            ),
        )
        assert second.continuations == ()

    def test_empty_page_exposes_no_item_follow_ups(self) -> None:
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ITEM_FOLLOW_UPS_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExamplePolicy",
                profiles=(),
            ),
            executor=ExampleExecutor(
                (
                    SirenMcpExecution(
                        status=200,
                        result={"items": [], "has_more": False, "next_offset": 0, "limit": 2},
                        base_url="https://api.example.test",
                    ),
                )
            ),
        )

        result = bridge.invoke(SirenMcpInvocation(operation_id="list_example_items", arguments={}))

        assert result.follow_ups == ()
        assert result.continuations == ()
        assert "entities" not in result.structured_content


class TestMcpItemFollowUpPolicy(McpCase):
    def test_unauthorized_item_targets_are_absent_from_siren_and_mcp_navigation(self) -> None:
        bridge = siren_mcp(
            siren_configuration(
                openapi="tests.support.applications.configuration.EXAMPLE_ITEM_FOLLOW_UPS_OPENAPI",
                source_path="/api",
                public_path="/siren",
                policy="tests.support.collaborators.ExampleListItemsOnlyPolicy",
                profiles=(),
            ),
            executor=ExampleExecutor(
                (
                    SirenMcpExecution(
                        status=200,
                        result={
                            "items": [{"item_id": "item-1", "expected_revision": "revision-1"}],
                            "has_more": True,
                            "next_offset": 1,
                            "limit": 1,
                        },
                        base_url="https://api.example.test",
                    ),
                )
            ),
        )

        result = bridge.invoke(SirenMcpInvocation(operation_id="list_example_items", arguments={}))

        assert result.follow_ups == ()
        assert len(result.continuations) == 1
        assert [link["rel"] for link in result.structured_content["entities"][0]["links"]] == [["self"]]
