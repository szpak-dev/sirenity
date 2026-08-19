from copy import deepcopy

import pytest

from sirenity import SirenContext, SirenityError, siren

from .openapi_documents import PARAMETER_MEDIA_SCHEMA


class TestFields:
    def test_public_facade_delegates_header_and_cookie_parameters(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records"]["get"]["parameters"].extend([
            {"name": "trace", "in": "header", "schema": {"type": "string"}},
            {"name": "session", "in": "cookie", "schema": {"type": "string"}},
        ])

        document = siren(document).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="record",
                capabilities=frozenset({"list_records"}),
            )
        )
        assert document.model_dump(by_alias=True, mode="json", exclude_none=True)["actions"][0]["fields"] == [
            {"name": "page", "type": "text", "title": "Page"}
        ]

    def test_public_facade_rejects_a_schema_less_parameter(self):
        invalid = deepcopy(PARAMETER_MEDIA_SCHEMA)
        invalid["paths"]["/records"]["get"]["parameters"] = [
            {"name": "filter", "in": "query", "required": False,
                "content": {"application/json": {}}}
        ]

        with pytest.raises(SirenityError):
            siren(invalid)

    def test_public_facade_rejects_duplicate_parameter_identities(self):
        invalid = deepcopy(PARAMETER_MEDIA_SCHEMA)
        invalid["paths"]["/records"]["get"]["parameters"] = [
            {"name": "filter", "in": "query", "required": False,
                "schema": {"type": "string"}},
            {"name": "filter", "in": "query", "required": False,
                "schema": {"type": "integer"}},
        ]

        with pytest.raises(SirenityError):
            siren(invalid)

    def test_public_facade_rejects_ambiguous_non_json_request_body_media(self):
        invalid = deepcopy(PARAMETER_MEDIA_SCHEMA)
        invalid["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"] = {
            "text/plain": {"schema": {"type": "string"}},
            "application/xml": {"schema": {"type": "string"}},
        }

        with pytest.raises(SirenityError):
            siren(invalid)

    @pytest.mark.parametrize(
        "schema",
        [
            {"type": "null"},
            {"oneOf": [{"type": "string"}, {"type": "integer"}]},
            {"type": "object", "properties": []},
            {"type": "object", "additionalProperties": "yes"},
        ],
    )
    def test_public_facade_rejects_unmappable_field_schemas(self, schema):
        invalid = deepcopy(PARAMETER_MEDIA_SCHEMA)
        invalid["paths"]["/records"]["get"]["parameters"] = [
            {"name": "value", "in": "query", "required": False, "schema": schema}
        ]

        with pytest.raises(SirenityError):
            siren(invalid)

    def test_public_facade_delegates_structured_inputs_and_non_json_bodies(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records"]["parameters"] = []
        document["paths"]["/records"]["get"]["parameters"] = [
            {"name": "page", "in": "query", "schema": {"type": "integer", "title": "Page"}},
            {"name": "filter", "in": "query", "schema": {
                "$ref": "#/components/schemas/Filter"}},
            {"name": "matrix", "in": "query", "schema": {
                "$ref": "#/components/schemas/Matrix"}},
            {"name": "trace", "in": "header", "schema": {"type": "string"}},
            {"name": "session", "in": "cookie", "schema": {"type": "string"}},
        ]
        document["components"] = {"schemas": {
            "Filter": {"type": "object", "additionalProperties": {"type": "string"}},
            "Matrix": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
            "Metadata": {"type": "object", "properties": {"source": {"type": "string"}}},
        }}
        body = document["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        body["properties"] = {
            "title": {"type": "string", "title": "Title"},
            "metadata": {"$ref": "#/components/schemas/Metadata"},
            "items": {"type": "array", "items": {"$ref": "#/components/schemas/Metadata"}},
        }

        engine = siren(document)
        collection = engine.project(SirenContext(
            base_url="https://api.example.com",
            scope="collection",
            resource="record",
            capabilities=frozenset({"list_records"}),
        )).model_dump(by_alias=True, mode="json", exclude_none=True)
        entity = engine.project(SirenContext(
            base_url="https://api.example.com",
            resource="record",
            value={"id": "42"},
            capabilities=frozenset({"replace_record"}),
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert collection["actions"][0]["fields"] == [
            {"name": "page", "type": "number", "title": "Page"}]
        assert entity["actions"][0]["fields"] == [
            {"name": "title", "type": "text", "title": "Title"}]

        document["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"] = {
            "text/plain": {}}
        delegated = siren(document).project(SirenContext(
            base_url="https://api.example.com",
            resource="record",
            value={"id": "42"},
            capabilities=frozenset({"replace_record"}),
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert delegated["actions"][0] == {
            "name": "replace_record",
            "href": "https://api.example.com/records/42",
            "method": "PATCH",
            "title": "Replace record",
            "type": "text/plain",
        }

    def test_public_facade_projects_common_openapi_controls(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records"]["parameters"] = []
        document["paths"]["/records"]["get"]["parameters"] = [
            {"name": "request_id", "in": "query", "required": True,
                "schema": {"type": "string", "format": "uuid", "title": "Request ID"}},
            {"name": "tags", "in": "query", "schema": {
                "type": "array", "items": {"type": "string"}}},
            {
                "name": "aliases",
                "in": "query",
                "schema": {"type": ["array", "null"], "items": {"type": "string"}},
            },
            {
                "name": "labels",
                "in": "query",
                "schema": {
                    "oneOf": [
                        {"type": "array", "minItems": 1,
                            "items": {"type": "string"}},
                        {"type": "null"},
                    ]
                },
            },
            {
                "name": "codes",
                "in": "query",
                "schema": {
                    "allOf": [
                        {"type": "array"},
                        {"items": {"type": "integer"}},
                        {"uniqueItems": True},
                    ]
                },
            },
            {"name": "status", "in": "query", "schema": {
                "type": "string", "title": "Status", "enum": ["draft", "published"]}},
            {
                "name": "scopes",
                "in": "query",
                "schema": {"type": "array", "title": "Scopes", "items": {"type": "string", "enum": ["read", "write"]}},
            },
            {"name": "nickname", "in": "query",
                "schema": {"type": ["string", "null"], "title": "Nickname"}},
            {
                "name": "external_id",
                "in": "query",
                "schema": {"title": "External ID", "oneOf": [{"type": "string", "format": "uuid"}, {"type": "null"}]},
            },
            {
                "name": "reference",
                "in": "query",
                "schema": {"title": "Reference", "allOf": [{"type": "string"}, {"format": "uuid"}]},
            },
        ]
        body = document["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        body["required"] = ["title"]
        body["properties"] = {
            "title": {"type": "string", "title": "Title"},
            "visibility": {
                "type": "string",
                "title": "Visibility",
                "enum": ["private", "public"],
                "default": "public",
            },
        }

        engine = siren(document)
        collection = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="record",
                capabilities=frozenset({"list_records"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        entity = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"id": "42"},
                capabilities=frozenset({"replace_record"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert collection["actions"][0]["fields"] == [
            {"name": "request_id", "type": "text", "title": "Request ID"},
            {
                "name": "status",
                "type": "radio",
                "title": "Status",
                "value": [{"value": "draft", "selected": False}, {"value": "published", "selected": False}],
            },
            {
                "name": "scopes",
                "type": "checkbox",
                "title": "Scopes",
                "value": [{"value": "read", "selected": False}, {"value": "write", "selected": False}],
            },
            {"name": "nickname", "type": "text", "title": "Nickname"},
            {"name": "external_id", "type": "text", "title": "External ID"},
            {"name": "reference", "type": "text", "title": "Reference"},
        ]
        operation_input = engine.operation_input("list_records")
        assert operation_input is not None
        assert operation_input.official_fields == (
            "request_id",
            "status",
            "scopes",
            "nickname",
            "external_id",
            "reference",
        )
        assert [value.name for value in operation_input.delegated_inputs] == [
            "tags",
            "aliases",
            "labels",
            "codes",
        ]
        assert [value.kind for value in operation_input.delegated_inputs] == [
            "array",
            "array",
            "array",
            "array",
        ]
        assert [value.definition for value in operation_input.delegated_inputs] == [
            {"type": "array", "items": {"type": "string"}},
            {"type": ["array", "null"], "items": {"type": "string"}},
            {
                "oneOf": [
                    {"type": "array", "minItems": 1, "items": {"type": "string"}},
                    {"type": "null"},
                ]
            },
            {
                "allOf": [
                    {"type": "array"},
                    {"items": {"type": "integer"}},
                    {"uniqueItems": True},
                ]
            },
        ]
        assert entity["actions"][0]["fields"] == [
            {"name": "title", "type": "text", "title": "Title"},
            {
                "name": "visibility",
                "type": "radio",
                "title": "Visibility",
                "value": [{"value": "private", "selected": False}, {"value": "public", "selected": True}],
            },
        ]

    @pytest.mark.parametrize("method", ["head", "options"])
    def test_public_facade_rejects_unsupported_http_methods(self, method):
        invalid = deepcopy(PARAMETER_MEDIA_SCHEMA)
        invalid["paths"]["/records"][method] = {
            "operationId": f"{method}_records",
            "responses": {"200": {"description": "OK"}},
        }

        with pytest.raises(SirenityError):
            siren(invalid)

    def test_public_facade_prefers_json_request_body_fields(self):
        document = siren(PARAMETER_MEDIA_SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"id": "42"},
                capabilities=frozenset({"replace_record"}),
            )
        )
        document = document.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        assert document["actions"][0]["fields"] == [
            {"name": "title", "type": "text", "title": "Title"}]

    def test_public_facade_maps_supported_query_and_json_body_fields(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        document["paths"]["/records"]["parameters"] = []
        document["paths"]["/records"]["get"]["parameters"] = [
            {"name": "text", "in": "query", "required": False,
                "schema": {"type": "string", "title": "Text"}},
            {"name": "email", "in": "query", "required": False,
                "schema": {"type": "string", "format": "email", "title": "Email"}},
            {"name": "uri", "in": "query", "required": False,
                "schema": {"type": "string", "format": "uri", "title": "URI"}},
            {"name": "date", "in": "query", "required": False,
                "schema": {"type": "string", "format": "date", "title": "Date"}},
            {
                "name": "date_time",
                "in": "query",
                "required": False,
                "schema": {"type": "string", "format": "date-time", "title": "Date time"},
            },
            {"name": "time", "in": "query", "required": False,
                "schema": {"type": "string", "format": "time", "title": "Time"}},
            {"name": "integer", "in": "query", "required": False,
                "schema": {"type": "integer", "title": "Integer"}},
            {"name": "number", "in": "query", "required": False,
                "schema": {"type": "number", "title": "Number"}},
            {"name": "boolean", "in": "query", "required": False,
                "schema": {"type": "boolean", "title": "Boolean"}},
        ]
        document["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["properties"] = {
            "title": {"type": "string", "title": "Title"},
            "priority": {"type": "integer", "title": "Priority"},
            "published": {"type": "boolean", "title": "Published"},
        }
        engine = siren(document)

        collection = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="record",
                capabilities=frozenset({"list_records"}),
            )
        )
        entity = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"id": "42"},
                capabilities=frozenset({"replace_record"}),
            )
        )
        collection = collection.model_dump(
            by_alias=True, mode="json", exclude_none=True)
        entity = entity.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        assert collection["actions"][0]["fields"] == [
            {"name": "text", "type": "text", "title": "Text"},
            {"name": "email", "type": "email", "title": "Email"},
            {"name": "uri", "type": "url", "title": "URI"},
            {"name": "date", "type": "date", "title": "Date"},
            {"name": "date_time", "type": "datetime-local", "title": "Date time"},
            {"name": "time", "type": "time", "title": "Time"},
            {"name": "integer", "type": "number", "title": "Integer"},
            {"name": "number", "type": "number", "title": "Number"},
            {"name": "boolean", "type": "checkbox", "title": "Boolean"},
        ]
        assert entity["actions"][0]["fields"] == [
            {"name": "title", "type": "text", "title": "Title"},
            {"name": "priority", "type": "number", "title": "Priority"},
            {"name": "published", "type": "checkbox", "title": "Published"},
        ]

    def test_public_facade_omits_boolean_defaults_that_siren_cannot_represent(self):
        document = deepcopy(PARAMETER_MEDIA_SCHEMA)
        body = document["paths"]["/records/{record_id}"]["patch"]["requestBody"]["content"]["application/json"][
            "schema"
        ]
        body["properties"] = {
            "dry_run": {"type": "boolean", "title": "Dry Run", "default": True},
        }

        projected = siren(document).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"record_id": "42"},
                capabilities=frozenset({"replace_record"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert projected["actions"][0]["fields"] == [
            {"name": "dry_run", "type": "checkbox", "title": "Dry Run"},
        ]
