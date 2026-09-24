from copy import deepcopy

import pytest

from sirenity.api import SirenAdapterPolicy, SirenAdapterRequest, SirenContractError, siren_adapter

from ..cases import CompilationCase


class TestPaginationContractAttacks(CompilationCase):
    def test_boundary_rejects_an_optional_declared_source_input(self) -> None:
        contract = self.contracts.explicit_pagination()
        del contract["paths"]["/api/example_records"]["get"]["parameters"][0]["required"]

        with pytest.raises(SirenContractError, match="source input must be required"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_invariant_rejects_incompatible_source_and_target_schemas(self) -> None:
        contract = self.contracts.explicit_pagination()
        link = contract["paths"]["/api/example_records"]["get"]["responses"]["200"]["links"]["next"]
        del link["parameters"]["example_offset"]
        link["x-sirenity"]["sourceInputs"] = {"query.example_offset": "$request.query.example_filter"}

        with pytest.raises(SirenContractError, match="schemas are incompatible"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_adversarial_contract_rejects_missing_required_has_more(self) -> None:
        contract = self.contracts.pagination()
        contract["components"]["schemas"]["ExampleRecordPage"]["required"].remove("has_more")

        with pytest.raises(SirenContractError, match="has_more property must be required"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_adversarial_contract_rejects_nullable_has_more(self) -> None:
        contract = self.contracts.pagination()
        contract["components"]["schemas"]["ExampleRecordPage"]["properties"]["has_more"] = {
            "anyOf": [{"type": "boolean"}, {"type": "null"}]
        }

        with pytest.raises(SirenContractError, match="non-nullable boolean has_more"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_adversarial_contract_rejects_an_ambiguous_item_collection(self) -> None:
        contract = self.contracts.pagination()
        page = contract["components"]["schemas"]["ExampleRecordPage"]
        page["properties"]["example_duplicates"] = {
            "type": "array",
            "items": {"$ref": "#/components/schemas/ExampleRecord"},
        }
        page["required"].append("example_duplicates")

        with pytest.raises(SirenContractError, match="exactly one array-of-object property"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_adversarial_contract_rejects_an_optional_item_collection(self) -> None:
        contract = self.contracts.pagination()
        contract["components"]["schemas"]["ExampleRecordPage"]["required"].remove("example_items")

        with pytest.raises(SirenContractError, match="items property must be required"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_adversarial_contract_rejects_an_optional_continuation_value(self) -> None:
        contract = self.contracts.pagination()
        contract["components"]["schemas"]["ExampleRecordPage"]["required"].remove("next_example_offset")

        with pytest.raises(SirenContractError, match="properties must exist and be required"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_adversarial_contract_rejects_a_nullable_continuation_value(self) -> None:
        contract = self.contracts.pagination()
        contract["components"]["schemas"]["ExampleRecordPage"]["properties"]["next_example_offset"] = {
            "anyOf": [{"type": "integer"}, {"type": "null"}]
        }

        with pytest.raises(SirenContractError, match="properties must be non-nullable scalars"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_adversarial_contract_rejects_a_different_target_operation(self) -> None:
        contract = self.contracts.pagination()
        contract["paths"]["/api/example_records"]["get"]["responses"]["200"]["links"]["next"]["operationId"] = (
            "get_example_record"
        )

        with pytest.raises(SirenContractError, match="same collection GET operation"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_invariant_rejects_pagination_without_a_query_continuation(self) -> None:
        contract = self.contracts.pagination()
        contract["paths"]["/api/example_records"]["get"]["responses"]["200"]["links"]["next"]["parameters"] = {}

        with pytest.raises(SirenContractError, match="same collection GET operation"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

    def test_cleanup_leaves_the_contract_unchanged_after_compilation(self) -> None:
        contract = self.contracts.pagination()
        original = deepcopy(contract)

        siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

        assert contract == original

    def test_recovery_accepts_a_valid_page_after_a_failed_contract(self) -> None:
        invalid = self.contracts.pagination()
        invalid["components"]["schemas"]["ExampleRecordPage"]["required"].remove("has_more")

        with pytest.raises(SirenContractError):
            siren_adapter(invalid, source_path="/api", public_path="/siren", profiles=())

        valid = siren_adapter(self.contracts.pagination(), source_path="/api", public_path="/siren", profiles=())
        assert valid.match("GET", "/siren/example_records") is not None


class TestPaginationContractHappyPaths(CompilationCase):
    def test_explicit_source_input_is_the_only_request_value_retained_by_a_typed_continuation(self) -> None:
        response = siren_adapter(
            self.contracts.explicit_pagination(),
            source_path="/api",
            public_path="/siren",
            profiles=(),
        ).respond(
            SirenAdapterRequest(
                operation_id="list_example_records",
                status=200,
                result={
                    "example_items": [],
                    "has_more": True,
                    "next_example_offset": 4,
                    "example_limit": 3,
                    "example_revision": "example-revision-8",
                },
                base_url="https://api.example.test",
                query=(
                    ("example_filter", "example-open"),
                    ("example_offset", 0),
                    ("example_limit", 99),
                    ("example_revision", "example-stale"),
                    ("example_noise", "example-excluded"),
                ),
                policy=SirenAdapterPolicy(all_capabilities=True),
            )
        )

        assert response.continuations[0].arguments == {
            "example_filter": "example-open",
            "example_offset": 4,
            "example_limit": 3,
            "example_revision": "example-revision-8",
        }
        assert response.payload["links"][-1]["href"] == (
            "https://api.example.test/siren/example_records?example_filter=example-open"
            "&example_offset=4&example_limit=3&example_revision=example-revision-8"
        )

    def test_incomplete_page_retains_the_existing_public_payload_contract(self) -> None:
        response = siren_adapter(
            self.contracts.pagination(), source_path="/api", public_path="/siren", profiles=()
        ).respond(
            SirenAdapterRequest(
                operation_id="list_example_records",
                status=200,
                result={
                    "example_items": [
                        {
                            "example_record_id": "example-record-1",
                            "example_title": "Example first",
                        }
                    ],
                    "has_more": True,
                    "next_example_offset": 2,
                    "example_limit": 2,
                    "example_revision": "example/revision 7",
                    "example_facets": ["example-featured"],
                },
                base_url="https://api.example.test",
                query=(
                    ("example_filter", "example-news"),
                    ("example_offset", 0),
                    ("example_limit", 2),
                ),
            )
        )

        assert response.payload["class"] == ["collection", "example-record"]
        assert response.payload["properties"] == {
            "has_more": True,
            "next_example_offset": 2,
            "example_limit": 2,
            "example_revision": "example/revision 7",
            "example_facets": ["example-featured"],
        }
        assert response.payload["links"][-1] == {
            "rel": ["next"],
            "title": "Next page",
            "href": (
                "https://api.example.test/siren/example_records?example_filter=example-news"
                "&example_offset=2&example_limit=2&example_revision=example%2Frevision%207"
            ),
        }
        assert len(response.continuations) == 1

    def test_final_page_exposes_no_continuation(self) -> None:
        response = siren_adapter(
            self.contracts.pagination(), source_path="/api", public_path="/siren", profiles=()
        ).respond(
            SirenAdapterRequest(
                operation_id="list_example_records",
                status=200,
                result={
                    "example_items": [],
                    "has_more": False,
                    "next_example_offset": 4,
                    "example_limit": 2,
                    "example_revision": "example-revision-7",
                },
                base_url="https://api.example.test",
            )
        )

        assert [link["rel"] for link in response.payload["links"]] == [["self"]]
        assert response.continuations == ()

    def test_declared_continuation_values_replace_stale_query_values(self) -> None:
        response = siren_adapter(
            self.contracts.pagination(), source_path="/api", public_path="/siren", profiles=()
        ).respond(
            SirenAdapterRequest(
                operation_id="list_example_records",
                status=200,
                result={
                    "example_items": [],
                    "has_more": True,
                    "next_example_offset": 4,
                    "example_limit": 3,
                    "example_revision": "example-revision-8",
                },
                base_url="https://api.example.test",
                query=(
                    ("example_filter", "example-a"),
                    ("example_filter", "example-b"),
                    ("example_offset", 0),
                    ("example_offset", 2),
                    ("example_limit", 2),
                ),
            )
        )

        assert response.payload["links"][-1]["href"] == (
            "https://api.example.test/siren/example_records?example_filter=example-a"
            "&example_filter=example-b&example_offset=4&example_limit=3"
            "&example_revision=example-revision-8"
        )
        assert response.continuations[0].arguments == {
            "example_filter": "example-b",
            "example_offset": 4,
            "example_limit": 3,
            "example_revision": "example-revision-8",
        }
