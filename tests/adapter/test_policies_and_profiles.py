import pytest

from sirenity.api import (
    SirenAdapterPolicy,
    SirenAdapterRequest,
    SirenAllowAllPolicy,
    SirenStructuredFormProfile,
    SirenityError,
    siren_adapter,
)

from ..cases import AdapterCase


class TestAdapterPolicyAndProfileAttacks(AdapterCase):
    def test_adversarial_policy_cannot_mix_explicit_and_all_capabilities(self) -> None:
        with pytest.raises(SirenityError, match="cannot combine"):
            SirenAdapterPolicy(
                capabilities=frozenset({"update_example_record"}),
                all_capabilities=True,
            )

    def test_invariant_profile_types_must_be_unique(self) -> None:
        with pytest.raises(SirenityError, match="profile types must be unique"):
            siren_adapter(
                self.contracts.operation(),
                profiles=(SirenStructuredFormProfile(), SirenStructuredFormProfile()),
            )

    def test_cleanup_default_projection_contains_no_opt_in_extension(self) -> None:
        response = siren_adapter(self.contracts.operation(), source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                operation_id="update_example_record",
                status=200,
                result={"example_record_id": "example-record-1", "example_title": "Example updated"},
                base_url="https://api.example.test",
                path_values={"example_record_id": "example-record-1"},
                policy=SirenAdapterPolicy(all_capabilities=True),
            )
        )

        assert "https://modwire.dev/siren/structured-form/v1" not in response.payload["actions"][0]

    def test_recovery_valid_adapter_builds_after_duplicate_profiles_are_rejected(self) -> None:
        with pytest.raises(SirenityError):
            siren_adapter(
                self.contracts.operation(),
                profiles=(SirenStructuredFormProfile(), SirenStructuredFormProfile()),
            )

        adapter = siren_adapter(self.contracts.operation(), profiles=(SirenStructuredFormProfile(),))
        assert adapter.match("PATCH", "/api/example_records/example-record-1") is not None


class TestAdapterPolicyAndProfileHappyPaths(AdapterCase):
    def test_allow_all_policy_selects_all_compiled_capabilities(self) -> None:
        policy = SirenAllowAllPolicy().select(
            "update_example_record",
            200,
            object(),
            {"example_record_id": "example-record-1"},
        )

        assert policy == SirenAdapterPolicy(all_capabilities=True)

    def test_explicit_capabilities_control_projected_actions(self) -> None:
        adapter = siren_adapter(self.contracts.entity(), source_path="/api", public_path="/siren")
        request = {
            "operation_id": "get_example_job",
            "status": 200,
            "result": {"example_job_id": "example-job-1", "example_state": "complete"},
            "base_url": "https://api.example.test",
            "path_values": {"example_job_id": "example-job-1"},
        }

        hidden = adapter.respond(SirenAdapterRequest(**request))
        exposed = adapter.respond(
            SirenAdapterRequest(
                **request,
                policy=SirenAdapterPolicy(capabilities=frozenset({"get_example_job"})),
            )
        )

        assert "actions" not in hidden.payload
        assert [action["name"] for action in exposed.payload["actions"]] == ["get_example_job"]

    def test_structured_form_profile_exposes_normalized_delegated_controls(self) -> None:
        adapter = siren_adapter(
            self.contracts.operation(),
            source_path="/api",
            public_path="/siren",
            profiles=(SirenStructuredFormProfile(),),
        )

        response = adapter.respond(
            SirenAdapterRequest(
                operation_id="update_example_record",
                status=200,
                result={"example_record_id": "example-record-1", "example_title": "Example updated"},
                base_url="https://api.example.test",
                path_values={"example_record_id": "example-record-1"},
                policy=SirenAdapterPolicy(all_capabilities=True),
            )
        )

        extension = response.payload["actions"][0]["https://modwire.dev/siren/structured-form/v1"]
        assert extension["version"] == "1"
        assert [control["name"] for control in extension["controls"]] == [
            "example_trace",
            "example_session",
            "example_metadata",
        ]
        assert extension["controls"][-1]["mediaType"] == "application/json"

    def test_profile_enrichment_does_not_leak_into_later_default_adapter(self) -> None:
        profiled = siren_adapter(
            self.contracts.operation(),
            profiles=(SirenStructuredFormProfile(),),
        )
        plain = siren_adapter(self.contracts.operation())
        request = SirenAdapterRequest(
            operation_id="update_example_record",
            status=200,
            result={"example_record_id": "example-record-1", "example_title": "Example updated"},
            base_url="https://api.example.test",
            path_values={"example_record_id": "example-record-1"},
            policy=SirenAdapterPolicy(all_capabilities=True),
        )

        enriched = profiled.respond(request)
        unmodified = plain.respond(request)

        extension = "https://modwire.dev/siren/structured-form/v1"
        assert extension in enriched.payload["actions"][0]
        assert extension not in unmodified.payload["actions"][0]
