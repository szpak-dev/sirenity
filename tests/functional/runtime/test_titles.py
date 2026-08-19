from copy import deepcopy
from typing import ClassVar

from sirenity import SirenContext, SirenRelationship, SirenResponseContext, SirenScope, siren


class TestTitles:
    schema: ClassVar[dict[str, object]] = {
        "openapi": "3.1.1",
        "info": {"title": "Example Service", "version": "4.0.0"},
        "paths": {
            "/articles": {
                "get": {
                    "operationId": "list_articles",
                    "summary": "Browse articles",
                    "responses": {
                        "200": {
                            "description": "Articles",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "title": "Published articles",
                                        "items": {"$ref": "#/components/schemas/Article"},
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "create_article",
                    "summary": "Create article",
                    "responses": {
                        "201": {
                            "description": "Article",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Article"}}
                            },
                        }
                    },
                },
            },
            "/articles/{article_id}": {
                "parameters": [
                    {
                        "name": "article_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_article",
                    "summary": "Read article",
                    "responses": {
                        "200": {
                            "description": "Article",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Article"}}
                            },
                        }
                    },
                },
            },
            "/authors/{author_id}": {
                "parameters": [
                    {
                        "name": "author_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_author",
                    "summary": "Read author",
                    "responses": {
                        "200": {
                            "description": "Author",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Author"}}
                            },
                        }
                    },
                },
            },
            "/articles/{article_id}/publish": {
                "parameters": [
                    {
                        "name": "article_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "post": {
                    "operationId": "publish_article",
                    "summary": "Publish article",
                    "responses": {
                        "202": {
                            "description": "Publication",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
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
                "Article": {
                    "type": "object",
                    "title": "Article",
                    "properties": {"article_id": {"type": "string"}},
                },
                "Author": {
                    "type": "object",
                    "title": "Author",
                    "properties": {"author_id": {"type": "string"}},
                },
            }
        },
    }

    def test_public_facade_prefers_exact_get_representation_titles_over_other_operations(self):
        document = deepcopy(self.schema)
        document["components"]["schemas"]["AlternateArticle"] = {
            "type": "object",
            "title": "Alternate article",
            "properties": {"article_id": {"type": "string"}},
        }
        document["paths"]["/articles/{article_id}"]["patch"] = {
            "operationId": "update_article",
            "responses": {
                "200": {
                    "description": "Alternate article",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AlternateArticle"}
                        }
                    },
                }
            },
        }

        projected = siren(document).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="article",
                value={"article_id": "42"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert projected["title"] == "Article"

    def test_public_facade_projects_root_metadata_action_summaries_and_collection_link_titles(self):
        document = siren(self.schema).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="root",
                capabilities=frozenset({"create_article"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document == {
            "class": ["api", "entry-point"],
            "title": "Example Service",
            "properties": {"version": "4.0.0"},
            "actions": [
                {
                    "name": "create_article",
                    "href": "https://api.example.com/articles",
                    "method": "POST",
                    "title": "Create article",
                }
            ],
            "links": [
                {
                    "title": "Example Service",
                    "rel": ["self"],
                    "href": "https://api.example.com/",
                },
                {
                    "title": "Published articles",
                    "rel": ["collection"],
                    "href": "https://api.example.com/articles",
                },
            ],
        }

    def test_public_facade_projects_schema_titles_for_collections_items_entities_and_links(self):
        engine = siren(self.schema)
        collection = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="article",
                items=({"article_id": "42"},),
                capabilities=frozenset({"list_articles"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        entity = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="article",
                value={"article_id": "42"},
                capabilities=frozenset({"get_article"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert collection["title"] == "Published articles"
        assert collection["links"] == [
            {
                "title": "Published articles",
                "rel": ["self"],
                "href": "https://api.example.com/articles",
            }
        ]
        assert collection["actions"][0]["title"] == "Browse articles"
        assert collection["entities"][0]["title"] == "Article"
        assert collection["entities"][0]["links"][0]["title"] == "Article"
        assert entity["title"] == "Article"
        assert entity["actions"][0]["title"] == "Read article"
        assert entity["links"][0]["title"] == "Article"

    def test_framework_response_wrapper_defers_to_the_resource_schema_title(self):
        document = deepcopy(self.schema)
        response_schema = document["paths"]["/articles"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        response_schema["title"] = "Response"

        projected = siren(document).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="article",
                items=({"article_id": "42"},),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert projected["title"] == "Article"
        assert projected["links"][0]["title"] == "Article"

    def test_item_dto_titles_do_not_leak_and_runtime_title_then_name_labels_items(self):
        document = deepcopy(self.schema)
        document["components"]["schemas"]["Article"]["title"] = "Scaffolding"
        response_schema = document["paths"]["/articles"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        response_schema.pop("title")
        response_schema["items"] = {
            "type": "object",
            "title": "ScaffoldingSummary",
            "properties": {
                "article_id": {"type": "string"},
                "title": {"type": "string"},
                "name": {"type": "string"},
            },
        }
        engine = siren(document)

        root = engine.project(SirenContext(
            base_url="https://api.example.com",
            scope="root",
        )).model_dump(by_alias=True, mode="json", exclude_none=True)
        collection = engine.project(SirenContext(
            base_url="https://api.example.com",
            scope="collection",
            resource="article",
            items=(
                {"article_id": "42", "title": "Visible title", "name": "Ignored name"},
                {"article_id": "43", "name": "Visible name"},
                {"article_id": "44", "title": "   ", "name": "Name after blank title"},
                {"article_id": "45", "title": 45, "name": "Name after numeric title"},
                {"article_id": "46"},
            ),
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

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
            "/authors/{author_id}/articles": document["paths"]["/articles"],
            "/authors/{author_id}/articles/{article_id}": document["paths"][
                "/articles/{article_id}"
            ],
        }
        document["paths"]["/authors/{author_id}/articles"]["parameters"] = [
            {
                "name": "author_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
        document["paths"]["/authors/{author_id}/articles/{article_id}"]["parameters"] = [
            {
                "name": "author_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            },
            {
                "name": "article_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            },
        ]

        projected = siren(document).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="article",
                path_values={"author_id": "7"},
                items=(
                    {
                        "article_id": "42",
                        "title": "Ignored first title",
                        "name": "Ignored first name",
                    },
                    {
                        "article_id": "43",
                        "title": "Ignored second title",
                        "name": "Ignored second name",
                    },
                ),
                item_titles=("First article", "Second article"),
                item_capabilities=(
                    frozenset({"get_article"}),
                    frozenset(),
                ),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert [item["title"] for item in projected["entities"]] == [
            "First article",
            "Second article",
        ]
        assert [item["links"][0]["title"] for item in projected["entities"]] == [
            "First article",
            "Second article",
        ]
        assert [item.get("actions", []) for item in projected["entities"]] == [
            [
                {
                    "name": "get_article",
                    "href": "https://api.example.com/authors/7/articles/42",
                    "method": "GET",
                    "title": "Read article",
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
                resource="article",
                title="Current selection",
                items=({"article_id": "42"},),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        entity = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="article",
                title="Current article",
                value={"article_id": "42"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert root["title"] == "Current service"
        assert root["links"][0]["title"] == "Current service"
        assert collection["title"] == "Current selection"
        assert collection["links"][0]["title"] == "Current selection"
        assert collection["entities"][0]["title"] == "Article"
        assert entity["title"] == "Current article"
        assert entity["links"][0]["title"] == "Current article"

    def test_relationships_apply_compiled_and_explicit_titles_to_links_and_embedded_entities(self):
        document = siren(self.schema).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="article",
                value={"article_id": "42"},
                relationships=(
                    SirenRelationship(
                        rel=("author",),
                        resource="author",
                        scope=SirenScope.ENTITY,
                        value={"author_id": "7"},
                    ),
                    SirenRelationship(
                        rel=("https://rels.example.com/editor",),
                        resource="author",
                        scope=SirenScope.ENTITY,
                        title="Editor profile",
                        value={"author_id": "8"},
                        embedded=True,
                    ),
                ),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["links"][1] == {
            "title": "Author",
            "rel": ["author"],
            "href": "https://api.example.com/authors/7",
        }
        assert document["entities"][0]["title"] == "Editor profile"
        assert document["entities"][0]["links"][0]["title"] == "Editor profile"

    def test_response_projection_uses_operation_titles_and_runtime_precedence_for_commands(self):
        engine = siren(self.schema)
        compiled = engine.project_response(
            SirenResponseContext(
                operation_id="publish_article",
                status=202,
                result={"published": True},
                representation="command",
                base_url="https://api.example.com",
                path_values={"article_id": "42"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        explicit = engine.project_response(
            SirenResponseContext(
                operation_id="publish_article",
                status=202,
                result={"published": True},
                representation="command",
                base_url="https://api.example.com",
                title="Published",
                path_values={"article_id": "42"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert compiled["title"] == "Publish article"
        assert compiled["links"][0]["title"] == "Publish article"
        assert explicit["title"] == "Published"
        assert explicit["links"][0]["title"] == "Published"

    def test_missing_resource_and_operation_metadata_does_not_generate_titles(self):
        document = {
            "openapi": "3.1.1",
            "info": {"title": "Untitled resources", "version": "1"},
            "paths": {
                "/records/{record_id}": {
                    "parameters": [
                        {
                            "name": "record_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_record",
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }

        projected = siren(document).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="record",
                value={"record_id": "42"},
                capabilities=frozenset({"get_record"}),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert "title" not in projected
        assert "title" not in projected["actions"][0]
        assert "title" not in projected["links"][0]
