import pytest

from sirenity.api import SirenAdapterRequest, SirenityError, siren_adapter

from ..cases import AdapterCase


class TestAdapterResponseAttacks(AdapterCase):
    def test_adversarial_unknown_successful_operation_is_rejected(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="unknown operation"):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id="get_missing_example_job",
                    status=200,
                    result={},
                    base_url="https://api.example.test",
                )
            )

    def test_invariant_successful_response_shape_must_match_the_contract(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="object response requires a mapping result"):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id="get_example_job",
                    status=200,
                    result=[],
                    base_url="https://api.example.test",
                    path_values={"example_job_id": "example-job-1"},
                )
            )

    def test_cleanup_removes_headers_bound_to_the_replaced_representation(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        response = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                    "next_example_cursor": "example-cursor-2",
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": "100",
                    "ETag": '"example-source"',
                    "Cache-Control": "private",
                    "X-Example-Trace": "example-trace-1",
                },
            )
        )

        assert response.headers == {
            "Cache-Control": "private",
            "X-Example-Trace": "example-trace-1",
        }

    def test_recovery_projects_a_valid_response_after_a_shape_failure(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id="get_example_job",
                    status=200,
                    result=[],
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
                    "next_example_cursor": "example-cursor-2",
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        )

        assert recovered.status == 200


class TestAdapterResponseHappyPaths(AdapterCase):
    def test_entity_response_has_official_siren_media_type_and_self_link(self) -> None:
        response = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                    "next_example_cursor": "example-cursor-2",
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        )

        assert response.media_type == "application/vnd.siren+json"
        assert response.payload["links"] == [
            {
                "title": "Example job state",
                "rel": ["self"],
                "href": "https://api.example.test/siren/example_jobs/example-job-1",
            }
        ]

    def test_unmatched_error_preserves_mapping_result_and_request_url(self) -> None:
        response = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                status=503,
                result={"example_detail": "example unavailable"},
                base_url="https://api.example.test",
                request_url="https://api.example.test/siren/example_jobs",
            )
        )

        assert response.payload == {
            "class": ["error"],
            "properties": {"example_detail": "example unavailable", "status": 503},
            "links": [
                {
                    "rel": ["self"],
                    "href": "https://api.example.test/siren/example_jobs",
                }
            ],
        }

    def test_unmatched_error_preserves_list_scalar_and_empty_results(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        listed = adapter.respond(
            SirenAdapterRequest(
                status=400,
                result=[{"example_detail": "example invalid"}],
                base_url="https://api.example.test",
            )
        )
        scalar = adapter.respond(
            SirenAdapterRequest(status=500, result="example failure", base_url="https://api.example.test")
        )
        empty = adapter.respond(SirenAdapterRequest(status=404, result=None, base_url="https://api.example.test"))

        assert listed.payload["properties"] == {
            "status": 400,
            "errors": [{"example_detail": "example invalid"}],
        }
        assert scalar.payload["properties"] == {"status": 500, "result": "example failure"}
        assert empty.payload["properties"] == {"status": 404}
