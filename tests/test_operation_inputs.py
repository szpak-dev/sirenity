from copy import deepcopy

import pytest
from openapi_documents import PARAMETER_MEDIA_SCHEMA

from sirenity import (
    SirenContext,
    SirenDelegatedInput,
    SirenInput,
    SirenityError,
    audit,
    siren,
)


class TestOperationInputs:
    def test_public_facade_exposes_resolved_official_and_delegated_input_metadata(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records"]["parameters"] = []
        document["paths"]["/records"]["get"]["parameters"] = [
            {"name": "page", "in": "query", "schema": {"type": "integer"}},
            {
                "name": "filter",
                "in": "query",
                "required": True,
                "style": "deepObject",
                "explode": True,
                "allowReserved": True,
                "schema": {"$ref": "#/components/schemas/Filter"},
            },
            {"name": "trace", "in": "header", "required": True,
                "schema": {"type": "string"}},
            {"name": "session", "in": "cookie",
                "explode": False, "schema": {"type": "string"}},
        ]
        document["components"] = {
            "requestBodies": {
                "RecordPatch": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RecordPatch"}
                        }
                    },
                }
            },
            "schemas": {
                "Filter": {
                    "type": "object",
                    "required": ["state"],
                    "properties": {"state": {"type": "string"}},
                },
                "Metadata": {
                    "type": "object",
                    "required": ["source"],
                    "properties": {"source": {"type": "string"}},
                },
                "RecordPatch": {
                    "type": "object",
                    "required": ["metadata", "items", "record_ids"],
                    "properties": {
                        "title": {"type": "string"},
                        "metadata": {"$ref": "#/components/schemas/Metadata"},
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Metadata"},
                        },
                        "record_ids": {
                            "type": "array",
                            "title": "Record IDs",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {"type": "string", "format": "uuid"},
                        },
                    },
                },
            },
        }
        document["paths"]["/records/{record_id}"]["patch"]["requestBody"] = {
            "$ref": "#/components/requestBodies/RecordPatch"
        }

        engine = siren(document)
        collection_input = engine.operation_input("list_records")
        body_input = engine.operation_input("replace_record")

        assert isinstance(collection_input, SirenInput)
        assert collection_input.media_type is None
        assert collection_input.definition is None
        assert collection_input.official_fields == ("page",)
        assert all(isinstance(value, SirenDelegatedInput)
                   for value in collection_input.delegated_inputs)
        assert [
            (
                value.name,
                value.location,
                value.kind,
                value.required,
                value.style,
                value.explode,
                value.allow_reserved,
                value.definition,
            )
            for value in collection_input.delegated_inputs
        ] == [
            (
                "filter",
                "query",
                "object",
                True,
                "deepObject",
                True,
                True,
                {
                    "type": "object",
                    "required": ["state"],
                    "properties": {"state": {"type": "string"}},
                },
            ),
            ("trace", "header", "json", True, "simple",
             False, False, {"type": "string"}),
            ("session", "cookie", "json", False,
             "form", False, False, {"type": "string"}),
        ]
        assert isinstance(body_input, SirenInput)
        assert body_input.media_type == "application/json"
        assert body_input.official_fields == ("title",)
        assert body_input.definition == {
            "type": "object",
            "required": ["metadata", "items", "record_ids"],
            "properties": {
                "title": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "required": ["source"],
                    "properties": {"source": {"type": "string"}},
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["source"],
                        "properties": {"source": {"type": "string"}},
                    },
                },
                "record_ids": {
                    "type": "array",
                    "title": "Record IDs",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"type": "string", "format": "uuid"},
                },
            },
        }
        assert [
            (value.name, value.location, value.kind,
             value.required, value.media_type)
            for value in body_input.delegated_inputs
        ] == [
            ("metadata", "body", "object", True, "application/json"),
            ("items", "body", "array", True, "application/json"),
            ("record_ids", "body", "array", True, "application/json"),
        ]
        assert body_input.delegated_inputs[0].definition == body_input.definition["properties"]["metadata"]
        assert body_input.delegated_inputs[1].definition == body_input.definition["properties"]["items"]
        assert body_input.delegated_inputs[2].definition == body_input.definition["properties"]["record_ids"]

        projected = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"id": "42"},
                capabilities=frozenset({"replace_record"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert projected["actions"][0]["fields"] == [
            {"name": "title", "type": "text"}]
        assert set(projected["actions"][0]) == {
            "name", "href", "method", "type", "fields"}
        assert audit(document).compatible is True

    def test_public_facade_exposes_one_non_json_body_as_delegated_input(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records/{record_id}"]["patch"]["requestBody"] = {
            "required": True,
            "content": {"text/plain": {"schema": {"type": "string", "minLength": 1}}},
        }

        operation_input = siren(document).operation_input("replace_record")

        assert operation_input == SirenInput(
            media_type="text/plain",
            definition={"type": "string", "minLength": 1},
            delegated_inputs=(
                SirenDelegatedInput(
                    name="body",
                    location="body",
                    kind="json",
                    required=True,
                    media_type="text/plain",
                    definition={"type": "string", "minLength": 1},
                ),
            ),
        )

    def test_public_facade_returns_none_without_inputs_and_wraps_unknown_operations(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records"]["parameters"] = []
        document["paths"]["/records"]["get"]["parameters"] = []
        engine = siren(document)

        assert engine.operation_input("list_records") is None
        with pytest.raises(SirenityError, match="Siren operation input lookup failed"):
            engine.operation_input("missing")
