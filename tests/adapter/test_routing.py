from sirenity.api import SirenAdapterRequest, siren_adapter

from ..cases import AdapterCase


class TestAdapterRoutingAttacks(AdapterCase):
    def test_adversarial_unknown_path_does_not_match(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        assert adapter.match("GET", "/siren/example_missing/example-job-1") is None
        assert adapter.dispatch_path("GET", "/siren/example_missing/example-job-1") is None

    def test_invariant_wrong_method_does_not_match_a_known_path(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        assert adapter.match("POST", "/siren/example_jobs/example-job-1") is None

    def test_cleanup_source_routes_are_not_rewritten_as_public_dispatches(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        assert adapter.dispatch_path("GET", "/api/example_jobs/example-job-1") is None

    def test_recovery_valid_path_matches_after_unknown_path(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        assert adapter.match("GET", "/siren/example_missing/example-job-1") is None
        assert adapter.match("GET", "/siren/example_jobs/example-job-1") is not None


class TestAdapterRoutingHappyPaths(AdapterCase):
    def test_source_and_public_mounts_resolve_the_same_operation(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        source = adapter.match("GET", "/api/example_jobs/example-job-1")
        public = adapter.match("GET", "/siren/example_jobs/example-job-1")

        assert source is not None
        assert public is not None
        assert source.operation_id == "get_example_job"
        assert public.operation_id == "get_example_job"
        assert source.path_values == {"example_job_id": "example-job-1"}
        assert public.path_values == {"example_job_id": "example-job-1"}

    def test_parameter_values_are_decoded_after_structural_matching(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        match = adapter.match("GET", "/siren/example_jobs/example%2Fjob%201")

        assert match is not None
        assert match.path_values == {"example_job_id": "example/job 1"}

    def test_public_route_renders_an_encoded_source_dispatch_path(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        assert adapter.dispatch_path("GET", "/siren/example_jobs/example%2Fjob%201") == (
            "/api/example_jobs/example%2Fjob%201"
        )

    def test_method_and_path_request_resolution_projects_the_matched_operation(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")

        response = adapter.respond(
            SirenAdapterRequest(
                method="GET",
                path="/siren/example_jobs/example-job-1",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "complete",
                    "has_more": False,
                    "next_example_cursor": "example-cursor-2",
                },
                base_url="https://api.example.test",
            )
        )

        assert response.status == 200
        assert response.payload["class"] == ["example-job"]
