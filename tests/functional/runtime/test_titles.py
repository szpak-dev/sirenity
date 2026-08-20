from copy import deepcopy
from typing import ClassVar

from sirenity import SirenContext, SirenRelationship, SirenResponseContext, SirenScope, siren


class TestTitles:
    schema: ClassVar[dict[str, object]] = {
        "openapi": "3.1.1",
        "info": {"title": "Example Service", "version": "4.0.0"},
        "paths": {
            "/example_resources": {
                "get": {
                    "operationId": "list_example_resources",
                    "summary": "Browse example resources",
                    "description": "Browse published example resources.",
                    "responses": {
                        "200": {
                            "description": "Example resources.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "title": "Published example resources",
                                        "items": {"$ref": "#/components/schemas/ExampleResource"},
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "create_example_resource",
                    "summary": "Create example resource",
                    "description": "Create an example resource.",
                    "responses": {
                        "201": {
                            "description": "Example resource.",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ExampleResource"}}
                            },
                        }
                    },
                },
            },
            "/example_resources/{example_resource_id}": {
                "parameters": [
                    {
                        "name": "example_resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_example_resource",
                    "summary": "Read example resource",
                    "description": "Read an example resource.",
                    "responses": {
                        "200": {
                            "description": "Example resource.",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ExampleResource"}}
                            },
                        }
                    },
                },
            },
            "/example_owners/{example_owner_id}": {
                "parameters": [
                    {
                        "name": "example_owner_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_example_owner",
                    "summary": "Read example owner",
                    "description": "Read an example owner.",
                    "responses": {
                        "200": {
                            "description": "Example owner.",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExampleOwner"}}},
                        }
                    },
                },
            },
            "/example_resources/{example_resource_id}/publish": {
                "parameters": [
                    {
                        "name": "example_resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "post": {
                    "operationId": "publish_example_resource",
                    "summary": "Publish example resource",
                    "description": "Publish an example resource.",
                    "responses": {
                        "202": {
                            "description": "Publication",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "Publication result",
                                        "properties": {"published": {"type": "boolean"}},
                                    }
                                }
                            },
                        }
                    },
                },
            },
        },
        "components": {
            "schemas": {
                "ExampleResource": {
                    "type": "object",
                    "title": "Example resource",
                    "properties": {"example_resource_id": {"type": "string"}},
                },
                "ExampleOwner": {
                    "type": "object",
                    "title": "Example owner",
                    "properties": {"example_owner_id": {"type": "string"}},
                },
            }
        },
    }

    def test_public_facade_prefers_exact_get_representation_titles_over_other_operations(self):
        document = deepcopy(self.schema)
        document["components"]["schemas"]["AlternateExampleResource"] = {
            "type": "object",
            "title": "Alternate example resource",
            "properties": {"example_resource_id": {"type": "string"}},
        }
        document["paths"]["/example_resources/{example_resource_id}"]["patch"] = {
            "operationId": "update_example_resource",
            "summary": "Update example resource",
            "description": "Update an example resource.",
            "responses": {
                "200": {
                    "description": "Alternate example resource.",
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/AlternateExampleResource"}}
                    },
                }
            },
        }

        projected = (
            siren(document)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="example_resource",
                    value={"example_resource_id": "42"},
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert projected["title"] == "Example resource"

    def test_public_facade_projects_root_metadata_action_summaries_and_collection_link_titles(self):
        document = (
            siren(self.schema)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="root",
                    capabilities=frozenset({"create_example_resource"}),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert document == {
            "class": ["api", "entry-point"],
            "title": "Example Service",
            "properties": {"version": "4.0.0"},
            "actions": [
                {
                    "name": "create_example_resource",
                    "href": "https://api.example.com/example_resources",
                    "method": "POST",
                    "title": "Create example resource",
                }
            ],
            "links": [
                {
                    "title": "Example Service",
                    "rel": ["self"],
                    "href": "https://api.example.com/",
                },
                {
                    "title": "Example resource",
                    "rel": ["collection"],
                    "href": "https://api.example.com/example_resources",
                },
            ],
        }

    def test_public_facade_projects_schema_titles_for_collections_items_entities_and_links(self):
        engine = siren(self.schema)
        collection = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                items=({"example_resource_id": "42"},),
                capabilities=frozenset({"list_example_resources"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        entity = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                value={"example_resource_id": "42"},
                capabilities=frozenset({"get_example_resource"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert collection["title"] == "Example resource"
        assert collection["links"] == [
            {
                "title": "Example resource",
                "rel": ["self"],
                "href": "https://api.example.com/example_resources",
            }
        ]
        assert collection["actions"][0]["title"] == "Browse example resources"
        assert collection["entities"][0]["title"] == "Example resource"
        assert collection["entities"][0]["links"][0]["title"] == "Example resource"
        assert entity["title"] == "Example resource"
        assert entity["actions"][0]["title"] == "Read example resource"
        assert entity["links"][0]["title"] == "Example resource"

    def test_array_response_title_does_not_replace_the_resource_schema_title(self):
        document = deepcopy(self.schema)
        response_schema = document["paths"]["/example_resources"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        response_schema["title"] = "Example collection wrapper"

        engine = siren(document)
        root = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="root",
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        collection = (
            engine.project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="collection",
                    resource="example_resource",
                    items=({"example_resource_id": "42"},),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert root["links"][1]["title"] == "Example resource"
        assert collection["title"] == "Example resource"
        assert collection["links"][0]["title"] == "Example resource"

    def test_item_dto_titles_do_not_leak_and_runtime_title_then_name_labels_items(self):
        document = deepcopy(self.schema)
        document["components"]["schemas"]["ExampleResource"]["title"] = "Scaffolding"
        response_schema = document["paths"]["/example_resources"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        response_schema["title"] = "Scaffolding"
        response_schema["items"] = {
            "type": "object",
            "title": "Scaffolding summary",
            "properties": {
                "example_resource_id": {"type": "string"},
                "title": {"type": "string"},
                "name": {"type": "string"},
            },
        }
        engine = siren(document)

        root = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="root",
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        collection = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                items=(
                    {"example_resource_id": "42", "title": "Visible title", "name": "Ignored name"},
                    {"example_resource_id": "43", "name": "Visible name"},
                    {"example_resource_id": "44", "title": "   ", "name": "Name after blank title"},
                    {"example_resource_id": "45", "title": 45, "name": "Name after numeric title"},
                    {"example_resource_id": "46"},
                ),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert root["links"][1]["title"] == "Scaffolding"
        assert collection["title"] == "Scaffolding"
        assert [item["title"] for item in collection["entities"]] == [
            "Visible title",
            "Visible name",
            "Name after blank title",
            "Name after numeric title",
            "Scaffolding",
        ]
        assert [item["links"][0]["title"] for item in collection["entities"]] == [
            "Visible title",
            "Visible name",
            "Name after blank title",
            "Name after numeric title",
            "Scaffolding",
        ]

    def test_runtime_item_titles_remain_aligned_with_nested_collection_capabilities(self):
        document = deepcopy(self.schema)
        document["paths"] = {
            "/example_owners/{example_owner_id}/example_resources": document["paths"]["/example_resources"],
            "/example_owners/{example_owner_id}/example_resources/{example_resource_id}": document["paths"][
                "/example_resources/{example_resource_id}"
            ],
        }
        document["paths"]["/example_owners/{example_owner_id}/example_resources"]["parameters"] = [
            {
                "name": "example_owner_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
        document["paths"]["/example_owners/{example_owner_id}/example_resources/{example_resource_id}"][
            "parameters"
        ] = [
            {
                "name": "example_owner_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            },
            {
                "name": "example_resource_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            },
        ]

        projected = (
            siren(document)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="collection",
                    resource="example_resource",
                    path_values={"example_owner_id": "7"},
                    items=(
                        {
                            "example_resource_id": "42",
                            "title": "Ignored first title",
                            "name": "Ignored first name",
                        },
                        {
                            "example_resource_id": "43",
                            "title": "Ignored second title",
                            "name": "Ignored second name",
                        },
                    ),
                    item_titles=("First example_resource", "Second example_resource"),
                    item_capabilities=(
                        frozenset({"get_example_resource"}),
                        frozenset(),
                    ),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert [item["title"] for item in projected["entities"]] == [
            "First example_resource",
            "Second example_resource",
        ]
        assert [item["links"][0]["title"] for item in projected["entities"]] == [
            "First example_resource",
            "Second example_resource",
        ]
        assert [item.get("actions", []) for item in projected["entities"]] == [
            [
                {
                    "name": "get_example_resource",
                    "href": "https://api.example.com/example_owners/7/example_resources/42",
                    "method": "GET",
                    "title": "Read example resource",
                }
            ],
            [],
        ]

    def test_runtime_titles_override_compiled_defaults_without_leaking_into_collection_items(self):
        engine = siren(self.schema)
        root = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="root",
                title="Current service",
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        collection = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                title="Current selection",
                items=({"example_resource_id": "42"},),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        entity = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                title="Current example resource",
                value={"example_resource_id": "42"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert root["title"] == "Current service"
        assert root["links"][0]["title"] == "Current service"
        assert collection["title"] == "Current selection"
        assert collection["links"][0]["title"] == "Current selection"
        assert collection["entities"][0]["title"] == "Example resource"
        assert entity["title"] == "Current example resource"
        assert entity["links"][0]["title"] == "Current example resource"

    def test_relationships_apply_compiled_and_explicit_titles_to_links_and_embedded_entities(self):
        document = (
            siren(self.schema)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="example_resource",
                    value={"example_resource_id": "42"},
                    relationships=(
                        SirenRelationship(
                            rel=("https://example.com/rels/example-owner",),
                            resource="example_owner",
                            scope=SirenScope.ENTITY,
                            value={"example_owner_id": "7"},
                        ),
                        SirenRelationship(
                            rel=("https://rels.example.com/editor",),
                            resource="example_owner",
                            scope=SirenScope.ENTITY,
                            title="Editor profile",
                            value={"example_owner_id": "8"},
                            embedded=True,
                        ),
                    ),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert document["links"][1] == {
            "title": "Example owner",
            "rel": ["https://example.com/rels/example-owner"],
            "href": "https://api.example.com/example_owners/7",
        }
        assert document["entities"][0]["title"] == "Editor profile"
        assert document["entities"][0]["links"][0]["title"] == "Editor profile"

    def test_response_projection_uses_operation_titles_and_runtime_precedence_for_commands(self):
        engine = siren(self.schema)
        compiled = engine.project_response(
            SirenResponseContext(
                operation_id="publish_example_resource",
                status=202,
                result={"published": True},
                representation="command",
                base_url="https://api.example.com",
                path_values={"example_resource_id": "42"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        explicit = engine.project_response(
            SirenResponseContext(
                operation_id="publish_example_resource",
                status=202,
                result={"published": True},
                representation="command",
                base_url="https://api.example.com",
                title="Published",
                path_values={"example_resource_id": "42"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert compiled["title"] == "Publish example resource"
        assert compiled["links"][0]["title"] == "Publish example resource"
        assert explicit["title"] == "Published"
        assert explicit["links"][0]["title"] == "Published"

    def test_operation_summary_generates_an_action_title_without_a_resource_title(self):
        document = {
            "openapi": "3.1.1",
            "info": {"title": "Untitled resources", "version": "1"},
            "paths": {
                "/example_resources/{example_resource_id}": {
                    "parameters": [
                        {
                            "name": "example_resource_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_example_resource",
                        "summary": "Read example resource",
                        "description": "Read an example resource.",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }

        projected = (
            siren(document)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="example_resource",
                    value={"example_resource_id": "42"},
                    capabilities=frozenset({"get_example_resource"}),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert "title" not in projected
        assert projected["actions"][0]["title"] == "Read example resource"
        assert "title" not in projected["links"][0]
