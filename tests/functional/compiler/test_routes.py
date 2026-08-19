from copy import deepcopy

import pytest

from sirenity import SirenContext, SirenityError, siren

from .openapi_documents import ROUTE_POLICY_SCHEMA, SCHEMA


class TestRoutes:
    def test_public_facade_derives_prefixed_collection_nested_and_entity_route_ownership(self):
        engine = siren(ROUTE_POLICY_SCHEMA, source_path="/api",
                       public_path="/hypermedia")
        collection = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="record",
                path_values={"team": "north/east"},
                capabilities=frozenset(
                    {"list_team_records", "search_team_records"}),
            )
        )
        entity = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"id": "r/42"},
                path_values={"team": "north/east"},
                capabilities=frozenset(
                    {"get_team_record", "archive_team_record"}),
            )
        )
        collection = collection.model_dump(
            by_alias=True, mode="json", exclude_none=True)
        entity = entity.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        assert collection["links"] == [
            {"rel": [
                "self"], "href": "https://api.example.com/hypermedia/v2/teams/north%2Feast/records"}
        ]
        assert collection["actions"] == [
            {
                "name": "list_team_records",
                "href": "https://api.example.com/hypermedia/v2/teams/north%2Feast/records",
                "method": "GET",
                "title": "List team records",
            },
            {
                "name": "search_team_records",
                "href": "https://api.example.com/hypermedia/v2/teams/north%2Feast/records/search",
                "method": "GET",
                "title": "Search team records",
            },
        ]
        assert entity["links"] == [
            {
                "rel": ["self"],
                "href": "https://api.example.com/hypermedia/v2/teams/north%2Feast/records/r%2F42",
            }
        ]
        assert entity["actions"] == [
            {
                "name": "get_team_record",
                "href": "https://api.example.com/hypermedia/v2/teams/north%2Feast/records/r%2F42",
                "method": "GET",
                "title": "Read team record",
            },
            {
                "name": "archive_team_record",
                "href": "https://api.example.com/hypermedia/v2/teams/north%2Feast/records/r%2F42/archive",
                "method": "POST",
                "title": "Archive team record",
            },
        ]

    def test_public_facade_uses_plural_static_subpaths_as_nested_resource_ownership(self):
        document = siren(ROUTE_POLICY_SCHEMA, source_path="/api", public_path="/hypermedia").project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="report",
                path_values={"team": "team", "record": "record"},
                capabilities=frozenset({"list_record_reports"}),
            )
        )
        document = document.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {
                "rel": ["self"],
                "href": "https://api.example.com/hypermedia/v2/teams/team/records/record/reports",
            }
        ]
        assert [action["name"]
                for action in document["actions"]] == ["list_record_reports"]

    def test_public_facade_uses_response_shape_to_distinguish_plural_entity_operations_from_collections(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Examples", "version": "1"},
            "paths": {
                "/examples": {
                    "get": {
                        "operationId": "list_examples",
                        "summary": "List examples",
                        "description": "List examples.",
                        "responses": {
                            "200": {
                                "description": "Examples",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "title": "Examples",
                                            "items": {"type": "object", "title": "Example"},
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                "/examples/{example_id}": {
                    "parameters": [
                        {
                            "name": "example_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_example",
                        "summary": "Read example",
                        "description": "Read an example.",
                        "responses": {
                            "200": {
                                "description": "Example",
                                "content": {
                                    "application/json": {"schema": {"type": "object", "title": "Example"}}
                                },
                            }
                        },
                    },
                },
                "/examples/{example_id}/metrics": {
                    "parameters": [
                        {
                            "name": "example_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "read_example_metrics",
                        "summary": "Read example metrics",
                        "description": "Read metrics for an example.",
                        "responses": {
                            "200": {
                                "description": "Metrics",
                                "content": {
                                    "application/json": {"schema": {"type": "object", "title": "Example metrics"}}
                                },
                            }
                        },
                    },
                },
                "/examples/{example_id}/events": {
                    "parameters": [
                        {
                            "name": "example_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "list_example_events",
                        "summary": "List example events",
                        "description": "List events for an example.",
                        "responses": {
                            "200": {
                                "description": "Events",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "title": "Example events",
                                            "items": {"type": "object", "title": "Example event"},
                                        }
                                    }
                                },
                            }
                        },
                    },
                },
            },
        }
        engine = siren(schema)

        entity = engine.project(SirenContext(
            base_url="https://api.example.com",
            resource="example",
            value={"id": "one"},
            path_values={"example_id": "one"},
            capabilities=frozenset({"read_example_metrics"}),
        )).model_dump(by_alias=True, mode="json", exclude_none=True)
        collection = engine.project(SirenContext(
            base_url="https://api.example.com",
            scope="collection",
            resource="event",
            path_values={"example_id": "one"},
            capabilities=frozenset({"list_example_events"}),
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert entity["actions"] == [
            {
                "name": "read_example_metrics",
                "href": "https://api.example.com/examples/one/metrics",
                "method": "GET",
                "title": "Read example metrics",
            }
        ]
        assert collection["links"] == [
            {"title": "Example events", "rel": ["self"], "href": "https://api.example.com/examples/one/events"}
        ]
        assert [action["name"]
                for action in collection["actions"]] == ["list_example_events"]

    def test_public_facade_projects_standalone_commands_as_concrete_root_actions(self):
        schema = deepcopy(SCHEMA)
        schema["paths"].update(
            {
                "/scaffoldings/converge": {
                    "post": {
                        "operationId": "converge_scaffoldings",
                        "summary": "Converge scaffoldings",
                        "description": "Converge scaffoldings.",
                        "responses": {"200": {"description": "OK"}},
                    }
                },
                "/scaffoldings/{scaffolding_id}/schema": {
                    "parameters": [
                        {
                            "name": "scaffolding_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_scaffolding_schema",
                        "summary": "Read scaffolding schema",
                        "description": "Read a scaffolding schema.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/scaffoldings/{scaffolding_id}/bundle": {
                    "parameters": [
                        {
                            "name": "scaffolding_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "post": {
                        "operationId": "bundle_scaffolding",
                        "summary": "Bundle scaffolding",
                        "description": "Bundle a scaffolding.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/scaffoldings/{scaffolding_id}/preview": {
                    "parameters": [
                        {
                            "name": "scaffolding_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "preview_scaffolding",
                        "summary": "Preview scaffolding",
                        "description": "Preview a scaffolding.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
            }
        )

        document = siren(schema, public_path="/hypermedia").project(
            SirenContext(
                base_url="https://api.example.com",
                scope="root",
                path_values={"scaffolding_id": "scaffolding/42"},
                capabilities=frozenset({
                    "converge_scaffoldings",
                    "get_scaffolding_schema",
                    "bundle_scaffolding",
                    "preview_scaffolding",
                }),
            )
        )
        document = document.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        assert document["actions"] == [
            {
                "name": "converge_scaffoldings",
                "href": "https://api.example.com/hypermedia/scaffoldings/converge",
                "method": "POST",
                "title": "Converge scaffoldings",
            },
            {
                "name": "get_scaffolding_schema",
                "href": "https://api.example.com/hypermedia/scaffoldings/scaffolding%2F42/schema",
                "method": "GET",
                "title": "Read scaffolding schema",
            },
            {
                "name": "bundle_scaffolding",
                "href": "https://api.example.com/hypermedia/scaffoldings/scaffolding%2F42/bundle",
                "method": "POST",
                "title": "Bundle scaffolding",
            },
            {
                "name": "preview_scaffolding",
                "href": "https://api.example.com/hypermedia/scaffoldings/scaffolding%2F42/preview",
                "method": "GET",
                "title": "Preview scaffolding",
            },
        ]

    def test_public_facade_rejects_invalid_routes_and_recovers(self):
        invalid = deepcopy(SCHEMA)
        invalid["paths"] = {
            "records": {
                "parameters": [],
                "get": {"operationId": "unknown", "responses": {"200": {"description": "OK"}}},
            }
        }

        with pytest.raises(SirenityError):
            siren(invalid)

        document = siren(ROUTE_POLICY_SCHEMA).project(
            SirenContext(base_url="https://api.example.com",
                         scope="collection", resource="label")
        )
        assert document.model_dump(by_alias=True, mode="json", exclude_none=True)["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/api/v2/labels"}
        ]

    def test_public_facade_rejects_indistinguishable_duplicate_resources_and_missing_path_values(self):
        invalid = deepcopy(ROUTE_POLICY_SCHEMA)
        invalid["paths"]["/api/v2/archives/{team}/records"] = {
            "parameters": [{"name": "team", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "operationId": "list_archived_records",
                "summary": "List archived records",
                "description": "List archived records.",
                "responses": {"200": {"description": "OK"}},
            },
        }

        with pytest.raises(SirenityError):
            siren(invalid)
        with pytest.raises(SirenityError, match="Siren projection failed"):
            siren(ROUTE_POLICY_SCHEMA).project(
                SirenContext(base_url="https://api.example.com",
                             scope="collection", resource="record")
            )

    def test_public_facade_selects_nested_duplicate_resources_from_parent_path_values_after_ambiguity(self):
        schema = deepcopy(SCHEMA)
        schema["paths"]["/sections/{section_id}/records"] = {
            "parameters": [{"name": "section_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "operationId": "list_section_records",
                "summary": "List section records",
                "description": "List records in a section.",
                "responses": {"200": {"description": "OK"}},
            },
        }
        schema["paths"]["/authors/{author_id}/records"] = {
            "parameters": [{"name": "author_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "operationId": "list_author_records",
                "summary": "List author records",
                "description": "List records by an author.",
                "responses": {"200": {"description": "OK"}},
            },
        }
        engine = siren(schema)

        with pytest.raises(SirenityError, match="Siren projection failed"):
            engine.project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="collection",
                    resource="record",
                    path_values={"section_id": "section",
                                 "author_id": "author"},
                )
            )

        document = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="record",
                path_values={"section_id": "section"},
                capabilities=frozenset({"list_section_records"}),
            )
        )
        document = document.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/sections/section/records"}]
        assert [action["name"]
                for action in document["actions"]] == ["list_section_records"]

    def test_public_facade_projects_trailing_slash_mounted_root_route(self):
        schema = deepcopy(SCHEMA)
        schema["paths"] = {f"/service{path}": item for path,
                           item in schema["paths"].items()}
        schema["paths"]["/service/"] = {
            "get": {
                "operationId": "get_api_root",
                "summary": "Read API root",
                "description": "Read the API root.",
                "responses": {"200": {"description": "OK"}},
            }
        }
        engine = siren(schema, source_path="/service/",
                       public_path="/hypermedia/")

        document = engine.project(SirenContext(
            base_url="https://api.example.com", scope="root", capabilities=frozenset({"get_api_root"})
        )).model_dump(by_alias=True, mode="json", exclude_none=True)
        assert document["links"] == [
            {"title": "Sirenity", "rel": [
                "self"], "href": "https://api.example.com/hypermedia"},
            {"rel": ["collection"],
                "href": "https://api.example.com/hypermedia/records"},
        ]
        assert document["actions"] == [
            {"name": "get_api_root",
                "href": "https://api.example.com/hypermedia", "method": "GET", "title": "Read API root"}
        ]

    def test_public_facade_rejects_path_item_references_and_trace_operations_without_losing_operations(self):
        referenced = deepcopy(SCHEMA)
        referenced["paths"]["/records"] = {
            "$ref": "#/components/pathItems/Records"}
        referenced["components"] = {
            "pathItems": {
                "Records": {"get": {"operationId": "list_records", "responses": {"200": {"description": "OK"}}}}
            }
        }

        with pytest.raises(SirenityError):
            siren(referenced)

        traced = deepcopy(SCHEMA)
        traced["paths"]["/records"]["trace"] = {
            "operationId": "trace_records",
            "responses": {"200": {"description": "OK"}},
        }

        with pytest.raises(SirenityError):
            siren(traced)

        document = siren(SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="record",
                capabilities=frozenset({"list_records"}),
            )
        )
        assert document.model_dump(by_alias=True, mode="json", exclude_none=True)["actions"] == [
            {"name": "list_records",
                "href": "https://api.example.com/records", "method": "GET", "title": "List records"}
        ]
