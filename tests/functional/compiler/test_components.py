from copy import deepcopy

import pytest

from sirenity import SirenContext, SirenityError, siren

from .openapi_documents import REFERENCED_SCHEMA


class TestComponents:
    def test_public_facade_rejects_an_invalid_openapi_document_and_recovers(self):
        invalid = deepcopy(REFERENCED_SCHEMA)
        invalid["paths"]["/example_resources/{example_resource_id}"]["parameters"][0]["required"] = False

        with pytest.raises(SirenityError):
            siren(invalid)

        document = siren(REFERENCED_SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                capabilities=frozenset({"list_example_resources"}),
            )
        )
        document = document.model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["actions"][0]["fields"] == [{"name": "page_size", "type": "number", "title": "Page size"}]

    @pytest.mark.parametrize(
        "reference",
        ["#/components/parameters/Missing", "#/components/schemas/PageSize", "#/components/parameters"],
    )
    def test_public_facade_rejects_invalid_component_references(self, reference):
        invalid = deepcopy(REFERENCED_SCHEMA)
        invalid["paths"]["/example_resources"]["get"]["parameters"] = [{"$ref": reference}]

        with pytest.raises(SirenityError):
            siren(invalid)

    def test_public_facade_rejects_a_cyclic_component_schema(self):
        cyclic = deepcopy(REFERENCED_SCHEMA)
        cyclic["components"]["schemas"]["Title"] = {"$ref": "#/components/schemas/Title"}

        with pytest.raises(SirenityError):
            siren(cyclic)

    def test_public_facade_projects_referenced_request_body_and_schema_siblings(self):
        document = siren(REFERENCED_SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                value={"id": "42"},
                capabilities=frozenset({"rename_example_resource"}),
            )
        )
        document = document.model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["actions"][0] == {
            "name": "rename_example_resource",
            "method": "PATCH",
            "href": "https://api.example.com/example_resources/42",
            "title": "Rename example resource",
            "type": "application/json",
            "fields": [{"name": "title", "type": "text", "title": "Title"}],
        }
