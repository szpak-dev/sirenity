from copy import deepcopy

import pytest

from sirenity.api import SirenAdapterRequest, SirenContractError, SirenityError, siren_adapter

from ..cases import CompilationCase


class TestBoundedContinuationContractAttacks(CompilationCase):
    def test_adversarial_contract_rejects_missing_required_has_more(self) -> None:
        contract = self.contracts.bounded()
        contract["components"]["schemas"]["ExampleJobState"]["required"].remove("has_more")

        with pytest.raises(SirenContractError, match="has_more property must be required"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_nullable_has_more(self) -> None:
        contract = self.contracts.bounded()
        contract["components"]["schemas"]["ExampleJobState"]["properties"]["has_more"] = {
            "anyOf": [{"type": "boolean"}, {"type": "null"}]
        }

        with pytest.raises(SirenContractError, match="non-nullable boolean has_more"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_non_boolean_has_more(self) -> None:
        contract = self.contracts.bounded()
        contract["components"]["schemas"]["ExampleJobState"]["properties"]["has_more"] = {"type": "integer"}

        with pytest.raises(SirenContractError, match="non-nullable boolean has_more"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_optional_continuation_value(self) -> None:
        contract = self.contracts.bounded()
        contract["components"]["schemas"]["ExampleJobState"]["required"].remove("next_example_cursor")

        with pytest.raises(SirenContractError, match="properties must exist and be required"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_nullable_continuation_value(self) -> None:
        contract = self.contracts.bounded()
        contract["components"]["schemas"]["ExampleJobState"]["properties"]["next_example_cursor"] = {
            "anyOf": [{"type": "string"}, {"type": "null"}]
        }

        with pytest.raises(SirenContractError, match="properties must be non-nullable scalars"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_structured_continuation_value(self) -> None:
        contract = self.contracts.bounded()
        contract["components"]["schemas"]["ExampleJobState"]["properties"]["next_example_cursor"] = {
            "type": "object",
            "properties": {"example_token": {"type": "string"}},
        }

        with pytest.raises(SirenContractError, match="properties must be non-nullable scalars"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_unknown_target(self) -> None:
        contract = self.contracts.bounded()
        link = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]["links"]["next"]
        link["operationId"] = "get_missing_example_job"

        with pytest.raises(SirenContractError, match="references unknown operation"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_unknown_target_parameter(self) -> None:
        contract = self.contracts.bounded()
        parameters = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]["links"][
            "next"
        ]["parameters"]
        parameters["example_unknown"] = "$response.body#/next_example_cursor"

        with pytest.raises(SirenContractError, match="does not match the target operation"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_unsupported_runtime_expression(self) -> None:
        contract = self.contracts.bounded()
        parameters = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]["links"][
            "next"
        ]["parameters"]
        parameters["example_cursor"] = "$request.query.example_cursor"

        with pytest.raises(SirenContractError, match="runtime expression is unsupported"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_adversarial_contract_rejects_more_than_one_continuation(self) -> None:
        contract = self.contracts.bounded()
        links = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]["links"]
        links["example_alternate"] = deepcopy(links["next"])

        with pytest.raises(SirenContractError, match="at most one continuation"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_invariant_rejects_non_object_continuation_responses(self) -> None:
        contract = self.contracts.bounded()
        response = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]
        response["content"]["application/json"]["schema"] = {
            "type": "array",
            "items": {"type": "object", "title": "Example job state"},
        }

        with pytest.raises(SirenContractError, match="continuation response requires object content"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_invariant_rejects_an_unsatisfied_required_target_query(self) -> None:
        contract = self.contracts.cross_operation_bounded()
        parameters = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]["links"][
            "next"
        ]["parameters"]
        del parameters["query.example_locale"]

        with pytest.raises(SirenContractError, match="required target query inputs"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_invariant_rejects_a_target_with_required_header_input(self) -> None:
        contract = self.contracts.cross_operation_bounded()
        target = contract["paths"]["/api/example_jobs/{example_job_id}/example_outputs/{example_output_id}"]["get"]
        target["parameters"].append(
            {
                "name": "example_trace",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "title": "Example trace"},
            }
        )

        with pytest.raises(SirenContractError, match="required header, cookie, or body inputs"):
            siren_adapter(contract, source_path="/api", public_path="/siren")

    def test_interruption_rejects_null_runtime_continuation_without_partial_output(self) -> None:
        adapter = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="continuation values cannot be null"):
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

    def test_cleanup_does_not_mutate_the_caller_contract_after_failure(self) -> None:
        contract = self.contracts.bounded()
        original = deepcopy(contract)
        contract["components"]["schemas"]["ExampleJobState"]["required"].remove("has_more")
        attacked = deepcopy(contract)

        with pytest.raises(SirenContractError):
            siren_adapter(contract, source_path="/api", public_path="/siren")

        assert contract == attacked
        assert original != contract

    def test_recovery_compiles_a_valid_contract_after_a_failed_contract(self) -> None:
        invalid = self.contracts.bounded()
        invalid["components"]["schemas"]["ExampleJobState"]["required"].remove("has_more")

        with pytest.raises(SirenContractError):
            siren_adapter(invalid, source_path="/api", public_path="/siren")

        adapter = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren")
        assert adapter.match("GET", "/siren/example_jobs/example-job-1") is not None


class TestBoundedContinuationContractHappyPaths(CompilationCase):
    def test_incomplete_non_collection_response_exposes_one_next_link_and_invocation(self) -> None:
        response = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "running",
                    "has_more": True,
                    "next_example_cursor": "example/cursor 2",
                    "example_notes": ["example-note"],
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
                query=(("example_filter", "example-open"), ("example_cursor", "example-old")),
            )
        )

        assert response.payload["class"] == ["example-job"]
        assert response.payload["links"][-1] == {
            "rel": ["next"],
            "title": "Read example job",
            "href": (
                "https://api.example.test/siren/example_jobs/example-job-1"
                "?example_filter=example-open&example_cursor=example%2Fcursor%202"
            ),
        }
        assert len(response.continuations) == 1
        assert response.continuations[0].operation_id == "get_example_job"
        assert response.continuations[0].arguments == {
            "example_job_id": "example-job-1",
            "example_filter": "example-open",
            "example_cursor": "example/cursor 2",
        }

    def test_final_response_omits_link_and_does_not_evaluate_missing_cursor(self) -> None:
        response = siren_adapter(self.contracts.bounded(), source_path="/api", public_path="/siren").respond(
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

        assert [link["rel"] for link in response.payload["links"]] == [["self"]]
        assert response.continuations == ()

    def test_bounded_response_allows_unrelated_array_properties(self) -> None:
        contract = self.contracts.bounded()
        properties = contract["components"]["schemas"]["ExampleJobState"]["properties"]
        properties["example_events"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"example_event": {"type": "string"}},
            },
        }
        response = siren_adapter(contract, source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "running",
                    "has_more": True,
                    "next_example_cursor": "example-cursor-2",
                    "example_events": [{"example_event": "example-event-1"}],
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        )

        assert response.payload["properties"]["example_events"] == [{"example_event": "example-event-1"}]
        assert len(response.continuations) == 1

    def test_standard_local_operation_reference_targets_the_continuation(self) -> None:
        contract = self.contracts.bounded()
        link = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]["links"]["next"]
        del link["operationId"]
        link["operationRef"] = "#/paths/~1api~1example_jobs~1{example_job_id}/get"

        response = siren_adapter(contract, source_path="/api", public_path="/siren").respond(
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

        assert response.continuations[0].operation_id == "get_example_job"

    def test_cross_operation_continuation_keeps_only_target_inputs(self) -> None:
        response = siren_adapter(
            self.contracts.cross_operation_bounded(),
            source_path="/api",
            public_path="/siren",
        ).respond(
            SirenAdapterRequest(
                operation_id="get_example_job",
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
                path_values={"example_job_id": "example-job-1"},
                query=(
                    ("example_filter", "example-open"),
                    ("example_cursor", "example-cursor-1"),
                    ("example_source_only", "example-source-only"),
                ),
            )
        )

        assert response.continuations[0].operation_id == "get_example_job_output"
        assert response.continuations[0].arguments == {
            "example_job_id": "example-job-1",
            "example_output_id": "example-output-2",
            "example_filter": "example-open",
            "example_locale": "example-en",
        }
        assert response.continuations[0].href == (
            "https://api.example.test/siren/example_jobs/example-job-1/example_outputs/example-output-2"
            "?example_filter=example-open&example_locale=example-en"
        )
