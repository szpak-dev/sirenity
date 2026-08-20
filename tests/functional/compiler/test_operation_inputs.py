from copy import deepcopy

import pytest

from sirenity import (
    SirenContext,
    SirenDelegatedInput,
    SirenInput,
    SirenityError,
    SirenParameterInput,
    audit,
    siren,
)

from .openapi_documents import PARAMETER_MEDIA_SCHEMA


class TestOperationInputs:
    def test_public_facade_exposes_resolved_official_and_delegated_input_metadata(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/example_resources"]["parameters"] = []
        document["paths"]["/example_resources"]["get"]["parameters"] = [
            {"name": "page", "in": "query", "schema": {"type": "integer", "title": "Page"}},
            {
                "name": "filter",
                "in": "query",
                "required": True,
                "style": "deepObject",
                "explode": True,
                "allowReserved": True,
                "schema": {"$ref": "#/components/schemas/Filter"},
            },
            {"name": "trace", "in": "header", "required": True, "schema": {"type": "string"}},
            {"name": "session", "in": "cookie", "explode": False, "schema": {"type": "string"}},
        ]
        document["components"] = {
            "requestBodies": {
                "ExampleResourcePatch": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExampleResourcePatch"}}},
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
                "ExampleResourcePatch": {
                    "type": "object",
                    "required": ["metadata", "items", "example_resource_ids"],
                    "properties": {
                        "title": {"type": "string", "title": "Title"},
                        "metadata": {"$ref": "#/components/schemas/Metadata"},
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Metadata"},
                        },
                        "example_resource_ids": {
                            "type": "array",
                            "title": "Example resource IDs",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {"type": "string", "format": "uuid"},
                        },
                    },
                },
            },
        }
        document["paths"]["/example_resources/{example_resource_id}"]["patch"]["requestBody"] = {
            "$ref": "#/components/requestBodies/ExampleResourcePatch"
        }

        engine = siren(document)
        collection_input = engine.operation_input("list_example_resources")
        body_input = engine.operation_input("replace_example_resource")

        assert isinstance(collection_input, SirenInput)
        assert collection_input.media_type is None
        assert collection_input.definition is None
        assert collection_input.official_fields == ("page",)
        assert all(isinstance(value, SirenDelegatedInput) for value in collection_input.delegated_inputs)
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
            ("trace", "header", "json", True, "simple", False, False, {"type": "string"}),
            ("session", "cookie", "json", False, "form", False, False, {"type": "string"}),
        ]
        assert isinstance(body_input, SirenInput)
        assert body_input.media_type == "application/json"
        assert body_input.official_fields == ("title",)
        assert body_input.definition == {
            "type": "object",
            "required": ["metadata", "items", "example_resource_ids"],
            "properties": {
                "title": {"type": "string", "title": "Title"},
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
                "example_resource_ids": {
                    "type": "array",
                    "title": "Example resource IDs",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"type": "string", "format": "uuid"},
                },
            },
        }
        assert [
            (value.name, value.location, value.kind, value.required, value.media_type)
            for value in body_input.delegated_inputs
        ] == [
            ("metadata", "body", "object", True, "application/json"),
            ("items", "body", "array", True, "application/json"),
            ("example_resource_ids", "body", "array", True, "application/json"),
        ]
        assert body_input.delegated_inputs[0].definition == body_input.definition["properties"]["metadata"]
        assert body_input.delegated_inputs[1].definition == body_input.definition["properties"]["items"]
        assert body_input.delegated_inputs[2].definition == body_input.definition["properties"]["example_resource_ids"]

        projected = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                value={"id": "42"},
                capabilities=frozenset({"replace_example_resource"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert projected["actions"][0]["fields"] == [{"name": "title", "type": "text", "title": "Title"}]
        assert set(projected["actions"][0]) == {"name", "href", "method", "title", "type", "fields"}
        assert audit(document).compatible is True

    def test_public_facade_exposes_one_non_json_body_as_delegated_input(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/example_resources/{example_resource_id}"]["patch"]["requestBody"] = {
            "required": True,
            "content": {"text/plain": {"schema": {"type": "string", "minLength": 1}}},
        }

        operation_input = siren(document).operation_input("replace_example_resource")

        assert operation_input == SirenInput(
            media_type="text/plain",
            definition={"type": "string", "minLength": 1},
            parameters=(
                SirenParameterInput(
                    name="example_resource_id",
                    location="path",
                    required=True,
                    definition={"type": "string"},
                ),
            ),
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
        document["paths"]["/example_resources"]["parameters"] = []
        document["paths"]["/example_resources"]["get"]["parameters"] = []
        engine = siren(document)

        assert engine.operation_input("list_example_resources") is None
        with pytest.raises(SirenityError, match="Siren operation input lookup failed"):
            engine.operation_input("missing")
