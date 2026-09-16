import pytest

from sirenity.api import SirenAdapterRequest, SirenityError, siren_adapter

from ..cases import AdapterCase


class TestFrameworkNeutralJourneyAttacks(AdapterCase):
    def test_adversarial_runtime_continuation_failure_exposes_no_partial_response(self) -> None:
        adapter = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="has_more value must be boolean"):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id="get_example_job",
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "running",
                        "has_more": "example-yes",
                        "next_example_cursor": "example-cursor-2",
                    },
                    base_url="https://api.example.test",
                    path_values={"example_job_id": "example-job-1"},
                )
            )

    def test_invariant_final_result_cannot_retain_a_previous_continuation(self) -> None:
        adapter = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren")
        first = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "running",
                    "has_more": True,
                    "next_example_cursor": "example-cursor-2",
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        )
        final = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        )

        assert len(first.continuations) == 1
        assert final.continuations == ()
        assert [link["rel"] for link in final.payload["links"]] == [["self"]]

    def test_recovery_same_adapter_projects_after_a_continuation_failure(self) -> None:
        adapter = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id="get_example_job",
                    status=200,
                    result={
                        "example_job_id": "example-job-1",
                        "example_state": "running",
                        "has_more": True,
                        "next_example_cursor": None,
                    },
                    base_url="https://api.example.test",
                    path_values={"example_job_id": "example-job-1"},
                )
            )
        recovered = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        )

        assert recovered.status == 200
        assert recovered.continuations == ()


class TestFrameworkNeutralJourneyHappyPaths(AdapterCase):
    def test_bounded_operation_moves_from_incomplete_to_final_response(self) -> None:
        adapter = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren")
        first = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "running",
                    "has_more": True,
                    "next_example_cursor": "example-cursor-2",
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
                query=(("example_cursor", "example-cursor-1"),),
            )
        )
        next_request = first.continuations[0]
        final = adapter.respond(
            SirenAdapterRequest(
                operation_id=next_request.operation_id,
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": next_request.arguments["example_job_id"]},
                query=(("example_cursor", next_request.arguments["example_cursor"]),),
            )
        )

        assert first.payload["links"][-1]["rel"] == ["next"]
        assert final.payload["properties"]["example_state"] == "complete"
        assert final.continuations == ()

    def test_pagination_moves_from_incomplete_to_final_page(self) -> None:
        adapter = siren_adapter(self.contracts.pagination(), source_path="/api", public_path="/siren")
        first = adapter.respond(
            SirenAdapterRequest(
                operation_id="list_example_records",
                status=200,
                result={
                    "example_items": [],
                    "has_more": True,
                    "next_example_offset": 2,
                    "example_limit": 2,
                    "example_revision": "example-revision-1",
                },
                base_url="https://api.example.test",
                query=(("example_offset", 0),),
            )
        )
        next_request = first.continuations[0]
        final = adapter.respond(
            SirenAdapterRequest(
                operation_id=next_request.operation_id,
                status=200,
                result={
                    "example_items": [],
                    "has_more": False,
                    "next_example_offset": 4,
                    "example_limit": 2,
                    "example_revision": "example-revision-1",
                },
                base_url="https://api.example.test",
                query=tuple(next_request.arguments.items()),
            )
        )

        assert first.payload["links"][-1]["rel"] == ["next"]
        assert final.continuations == ()
