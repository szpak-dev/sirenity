from copy import deepcopy

import pytest

from sirenity.api import SirenContractError, audit

from ..cases import AuditCase


class TestCompatibilityAuditAttacks(AuditCase):
    def test_adversarial_non_openapi_document_is_rejected(self) -> None:
        with pytest.raises(SirenContractError, match="does not conform to OpenAPI 3.1"):
            audit({"openapi": "3.1.1", "info": {}, "paths": []})

    def test_invariant_non_json_value_is_rejected_before_a_report_is_created(self) -> None:
        contract = self.contracts.entity()
        contract["x-example-value"] = object()

        with pytest.raises(SirenContractError, match="must be JSON-compatible"):
            audit(contract)

    def test_cleanup_audit_does_not_mutate_the_caller_contract(self) -> None:
        contract = self.contracts.entity()
        original = deepcopy(contract)

        audit(contract)

        assert contract == original

    def test_recovery_valid_audit_succeeds_after_invalid_input(self) -> None:
        with pytest.raises(SirenContractError):
            audit({"openapi": "3.1.1", "info": {}, "paths": []})

        recovered = audit(self.contracts.entity())

        assert recovered.compatible is True


class TestCompatibilityAuditHappyPaths(AuditCase):
    def test_compatible_contract_returns_an_empty_report(self) -> None:
        report = audit(self.contracts.entity())

        assert report.compatible is True
        assert report.findings == ()
        assert report.render() == "OpenAPI-to-Siren compatibility: compatible"

    def test_audit_reports_every_caller_actionable_finding(self) -> None:
        contract = self.contracts.entity()
        operation = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]
        del operation["summary"]
        del operation["description"]
        contract["paths"]["/api/example_jobs/{example_job_id}"]["head"] = {
            "operationId": "head_example_job",
            "summary": "Inspect example job",
            "description": "Inspect one example job.",
            "responses": {"200": {"description": "Example response."}},
        }

        report = audit(contract)

        assert report.compatible is False
        assert [(finding.category, finding.location) for finding in report.findings] == [
            (
                "operation-description",
                "#/paths/~1api~1example_jobs~1{example_job_id}/get/description",
            ),
            (
                "operation-summary",
                "#/paths/~1api~1example_jobs~1{example_job_id}/get/summary",
            ),
            (
                "http-method",
                "#/paths/~1api~1example_jobs~1{example_job_id}/head",
            ),
        ]

    def test_rendered_findings_include_detail_and_remediation(self) -> None:
        contract = self.contracts.entity()
        del contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["summary"]

        rendered = audit(contract).render()

        assert "[operation-summary]" in rendered
        assert "OpenAPI operation requires a non-empty summary" in rendered
        assert "Remediation: Provide a non-empty summary" in rendered
