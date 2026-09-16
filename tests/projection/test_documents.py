import pytest

from sirenity.api import (
    SirenContext,
    SirenResponseContext,
    SirenScope,
    SirenityError,
    siren,
)

from ..cases import ProjectionCase


class TestDocumentProjectionAttacks(ProjectionCase):
    def test_adversarial_unknown_resource_is_rejected(self) -> None:
        engine = siren(self.contracts.entity(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="unknown resource"):
            engine.project(
                SirenContext(
                    base_url="https://api.example.test",
                    resource="example_missing",
                    value={"example_missing_id": "example-missing-1"},
                )
            )

    def test_invariant_entity_path_value_must_be_available(self) -> None:
        engine = siren(self.contracts.entity(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="requires path value: example_job_id"):
            engine.project(
                SirenContext(
                    base_url="https://api.example.test",
                    resource="example_job",
                    value={"example_state": "complete"},
                )
            )

    def test_invariant_collection_titles_must_align_with_items(self) -> None:
        with pytest.raises(SirenityError, match="item titles must align"):
            SirenContext(
                base_url="https://api.example.test",
                scope=SirenScope.COLLECTION,
                resource="example_record",
                items=({"example_record_id": "example-record-1"},),
                item_titles=("Example first", "Example second"),
            )

    def test_invariant_response_must_reference_a_compiled_operation(self) -> None:
        engine = siren(self.contracts.entity(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="unknown operation"):
            engine.project_response(
                SirenResponseContext(
                    operation_id="get_example_missing",
                    status=200,
                    result={},
                    base_url="https://api.example.test",
                )
            )

    def test_cleanup_failed_projection_does_not_change_later_documents(self) -> None:
        engine = siren(self.contracts.entity(), source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError):
            engine.project(
                SirenContext(
                    base_url="https://api.example.test",
                    resource="example_job",
                    value={"example_state": "running"},
                )
            )
        recovered = engine.project(
            SirenContext(
                base_url="https://api.example.test",
                resource="example_job",
                value={"example_job_id": "example-job-1", "example_state": "complete"},
            )
        )

        assert recovered.properties == {
            "example_job_id": "example-job-1",
            "example_state": "complete",
        }


class TestDocumentProjectionHappyPaths(ProjectionCase):
    def test_root_projects_api_metadata_and_collection_discovery(self) -> None:
        engine = siren(self.contracts.pagination(), source_path="/api", public_path="/siren")

        document = engine.project(
            SirenContext(
                base_url="https://api.example.test",
                scope=SirenScope.ROOT,
                value={"example_status": "available", "version": "caller-version"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["class"] == ["api", "entry-point"]
        assert document["title"] == "Example records API"
        assert document["properties"] == {
            "example_status": "available",
            "version": "1.0.0",
        }
        assert document["links"][-1] == {
            "title": "Example record",
            "rel": ["collection"],
            "href": "https://api.example.test/siren/example_records",
        }

    def test_collection_projects_items_with_independent_capabilities(self) -> None:
        engine = siren(self.contracts.pagination(), source_path="/api", public_path="/siren")

        document = engine.project(
            SirenContext(
                base_url="https://api.example.test",
                scope=SirenScope.COLLECTION,
                resource="example_record",
                items=(
                    {"example_record_id": "example-record-1", "example_title": "Example first"},
                    {"example_record_id": "example-record-2", "example_title": "Example second"},
                ),
                item_titles=("Example first", "Example second"),
                item_capabilities=(frozenset({"get_example_record"}), frozenset()),
                capabilities=frozenset({"list_example_records"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["class"] == ["collection", "example-record"]
        assert document["entities"][0]["title"] == "Example first"
        assert document["entities"][0]["actions"][0]["name"] == "get_example_record"
        assert "actions" not in document["entities"][1]

    def test_entity_query_is_preserved_in_self_and_action_targets(self) -> None:
        engine = siren(self.contracts.entity(), source_path="/api", public_path="/siren")

        document = engine.project(
            SirenContext(
                base_url="https://api.example.test",
                resource="example_job",
                value={"example_job_id": "example-job-1", "example_state": "running"},
                query=(("example_filter", "example open"), ("example_filter", "example queued")),
                capabilities=frozenset({"get_example_job"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        target = "?example_filter=example%20open&example_filter=example%20queued"
        assert document["links"][0]["href"].endswith(target)
        assert document["actions"][0]["href"].endswith(target)

    def test_operation_aware_projection_uses_executed_response_shape(self) -> None:
        engine = siren(self.contracts.entity(), source_path="/api", public_path="/siren")

        document = engine.project_response(
            SirenResponseContext(
                operation_id="get_example_job",
                status=200,
                result={"example_job_id": "example-job-1", "example_state": "complete"},
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["class"] == ["example-job"]
        assert document["properties"]["example_state"] == "complete"
        assert document["links"][0]["href"] == ("https://api.example.test/siren/example_jobs/example-job-1")
