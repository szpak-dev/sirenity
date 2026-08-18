from copy import deepcopy

import pytest
from openapi_documents import PARAMETER_MEDIA_SCHEMA

from sirenity import SirenityError, audit, siren


class TestCompatibility:
    def test_public_facade_reports_all_independent_compatibility_findings_in_deterministic_order(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records"]["get"]["parameters"] = [
            {"name": "session", "in": "header",
                "required": False, "schema": {"type": "string"}},
            {"name": "query", "in": "query", "required": True,
                "schema": {"type": "string"}},
            {
                "name": "tags",
                "in": "query",
                "required": False,
                "schema": {"type": "array", "items": {"type": "string"}},
            },
        ]
        document["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"] = {
            "text/plain": {"schema": {"type": "string"}},
            "application/xml": {"schema": {"type": "string"}},
        }
        document["paths"]["/records"]["head"] = {
            "operationId": "head_records",
            "responses": {"200": {"description": "OK"}},
        }

        report = audit(document)

        assert report.compatible is False
        assert [(finding.category, finding.location) for finding in report.findings] == [
            ("http-method", "#/paths/~1records/head"),
            ("body-media-type",
             "#/paths/~1records~1{record_id}/patch/requestBody/content"),
        ]
        assert report.render() == (
            "OpenAPI-to-Siren compatibility findings:\n"
            "- #/paths/~1records/head [http-method]: OpenAPI operation method is unsupported: HEAD /records. "
            "Remediation: Use an official Siren action method: GET, POST, PUT, PATCH, or DELETE.\n"
            "- #/paths/~1records~1{record_id}/patch/requestBody/content [body-media-type]: OpenAPI request body media "
            "types are ambiguous. Remediation: Provide application/json or exactly one declared request media type."
        )

    def test_public_facade_reports_a_compatible_contract_without_changing_fail_fast_compilation(self):
        report = audit(PARAMETER_MEDIA_SCHEMA)

        assert report.compatible is True
        assert report.findings == ()
        assert report.render() == "OpenAPI-to-Siren compatibility: compatible"

        incompatible = deepcopy(PARAMETER_MEDIA_SCHEMA)
        incompatible["paths"]["/records"]["get"]["parameters"] = [
            {"name": "page", "in": "query", "schema": {
                "type": "string", "format": "hostname"}}
        ]

        with pytest.raises(SirenityError):
            siren(incompatible)

    def test_public_facade_audits_response_shapes_with_the_strict_compiler_policy(self):
        incompatible = deepcopy(PARAMETER_MEDIA_SCHEMA)
        incompatible["paths"]["/records"]["get"]["responses"]["200"]["content"] = {
            "application/json": {"schema": {"type": "string"}}
        }

        report = audit(incompatible)

        assert [(finding.category, finding.location) for finding in report.findings] == [
            ("response-schema", "#/paths/~1records/get/responses")
        ]
        assert report.findings[0].detail == (
            "OpenAPI response schema must be an object or array: 200 application/json"
        )
        with pytest.raises(SirenityError):
            siren(incompatible)
