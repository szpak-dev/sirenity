from copy import deepcopy

import pytest

from sirenity import SirenContext, SirenContractError, SirenityError, siren

from .openapi_documents import SCHEMA


class TestErrors:
    def test_public_facade_emits_a_structured_input_error(self):
        with pytest.raises(SirenContractError) as raised:
            siren([])

        assert raised.value.location == "#"
        assert raised.value.category == "input"
        assert raised.value.detail == "OpenAPI document must be a mapping."

    def test_public_facade_projects_a_supported_openapi_enum_control(self):
        document = deepcopy(SCHEMA)
        document["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["properties"]["title"] = {
            "type": "string",
            "title": "Publication state",
            "enum": ["draft", "published"],
        }

        result = siren(document).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"record_id": "42"},
                capabilities=frozenset({"rename_record"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert result["actions"][0]["fields"] == [
            {
                "name": "title",
                "type": "radio",
                "title": "Publication state",
                "value": [{"value": "draft", "selected": False}, {"value": "published", "selected": False}],
            }
        ]

    @pytest.mark.parametrize(
        "context",
        [
            SirenContext(base_url="https://api.example.com",
                         resource="record"),
            SirenContext(base_url="https://api.example.com",
                         resource="unknown"),
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"id": "42"},
                capabilities=frozenset({"unknown_operation"}),
            ),
        ],
    )
    def test_engine_chains_context_failures_as_projection_errors(self, context):
        with pytest.raises(SirenityError, match="Siren projection failed") as raised:
            siren(SCHEMA).project(context)

        assert raised.value.__cause__ is not None

    def test_public_facade_recovers_with_compilation_and_projection_success(self):
        document = siren(SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"id": "42"},
                capabilities=frozenset({"get_record"}),
            )
        )
        document = document.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/records/42"}]
