from copy import deepcopy
from typing import ClassVar

import pytest

from sirenity import SirenContractError, SirenityError, SirenResponseContext, siren


class TestResponses:
    schema: ClassVar[dict[str, object]] = {
        "openapi": "3.1.1",
        "info": {"title": "Response projection", "version": "1"},
        "paths": {
            "/articles": {
                "get": {
                    "operationId": "list_articles",
                    "responses": {
                        "200": {
                            "description": "Articles",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Article"},
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "create_article",
                    "responses": {
                        "201": {
                            "$ref": "#/components/responses/ArticleCreated",
                        }
                    },
                },
            },
            "/articles/{article_key}": {
                "parameters": [
                    {
                        "name": "article_key",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_article",
                    "responses": {
                        "200": {
                            "description": "Article",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Article"}}
                            },
                        },
                        "404": {
                            "description": "Missing article",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Problem"}
                                },
                                "application/problem+json": {
                                    "schema": {"$ref": "#/components/schemas/Problem"}
                                }
                            },
                        },
                    },
                },
                "patch": {
                    "operationId": "update_article",
                    "responses": {
                        "200": {
                            "description": "Updated article",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Article"}}
                            },
                        }
                    },
                },
                "delete": {
                    "operationId": "delete_article",
                    "responses": {"204": {"description": "Deleted"}},
                },
            },
            "/articles/{article_key}/publish": {
                "parameters": [
                    {
                        "name": "article_key",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "post": {
                    "operationId": "publish_article",
                    "responses": {
                        "202": {
                            "description": "Publication result",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PublicationResult"}
                                }
                            },
                        }
                    },
                },
            },
            "/maintenance/reindex": {
                "post": {
                    "operationId": "reindex",
                    "responses": {
                        "202": {
                            "description": "Reindex result",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ReindexResult"}
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "responses": {
                "ArticleCreated": {
                    "description": "Created article",
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/Article"}}
                    },
                }
            },
            "schemas": {
                "Article": {
                    "type": "object",
                    "required": ["article_key", "title"],
                    "properties": {
                        "article_key": {"type": "string"},
                        "title": {"type": "string"},
                    },
                },
                "Problem": {
                    "type": "object",
                    "required": ["detail"],
                    "properties": {"detail": {"type": "string"}},
                },
                "PublicationResult": {
                    "type": "object",
                    "properties": {"published": {"type": "boolean"}},
                },
                "ReindexResult": {
                    "type": "object",
                    "properties": {"accepted": {"type": "boolean"}},
                },
            },
        },
    }

    def test_public_engine_projects_declared_array_responses_as_collections(self):
        document = siren(self.schema).project_response(SirenResponseContext(
            operation_id="list_articles",
            status=200,
            result=[{"article_key": "first", "title": "First"}],
            base_url="https://api.example.com",
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document == {
            "class": ["collection", "article"],
            "properties": {},
            "entities": [
                {
                    "class": ["article"],
                    "title": "First",
                    "rel": ["item"],
                    "properties": {"article_key": "first", "title": "First"},
                    "links": [
                        {
                            "title": "First",
                            "rel": ["self"],
                            "href": "https://api.example.com/articles/first",
                        }
                    ],
                }
            ],
            "links": [{"rel": ["self"], "href": "https://api.example.com/articles"}],
        }

    def test_public_engine_projects_openapi_response_links_without_runtime_relationship_policy(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/articles/{article_key}"]["get"]["responses"]["200"]["links"] = {
            "articleCollection": {
                "operationId": "list_articles",
                "x-sirenity": {"rel": "collection", "scope": "collection"},
            }
        }
        schema["paths"]["/articles/{article_key}"]["patch"]["responses"]["200"]["links"] = {
            "article": {
                "operationRef": "#/paths/~1articles~1{article_key}/get",
                "parameters": {"path.article_key": "$response.body#/article_key"},
                "x-sirenity": {"rel": ["self", "canonical"], "scope": "entity"},
            }
        }

        entity = siren(schema).project_response(SirenResponseContext(
            operation_id="get_article",
            status=200,
            result={"article_key": "42", "title": "Linked"},
            base_url="https://api.example.com",
        )).model_dump(by_alias=True, mode="json", exclude_none=True)
        command = siren(schema).project_response(SirenResponseContext(
            operation_id="update_article",
            status=200,
            result={"article_key": "42", "title": "Linked"},
            base_url="https://api.example.com",
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert entity["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/articles/42"},
            {"rel": ["collection"], "href": "https://api.example.com/articles"},
        ]
        assert command["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/articles/42"},
            {
                "rel": ["self", "canonical"],
                "href": "https://api.example.com/articles/42",
            },
        ]

    def test_public_engine_rejects_invalid_openapi_response_link_bindings(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/articles/{article_key}"]["get"]["responses"]["200"]["links"] = {
            "article": {
                "operationId": "get_article",
                "parameters": {"article_key": "$response.body#/missing"},
                "x-sirenity": {"rel": "canonical", "scope": "entity"},
            }
        }

        with pytest.raises(SirenityError, match="Siren response projection failed"):
            siren(schema).project_response(SirenResponseContext(
                operation_id="get_article",
                status=200,
                result={"article_key": "42", "title": "Linked"},
                base_url="https://api.example.com",
            ))

    def test_public_engine_projects_a_nested_collection_response_link(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Diagram sets", "version": "1"},
            "paths": {
                "/diagram-sets/{diagram_set_id}": {
                    "parameters": [{
                        "name": "diagram_set_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }],
                    "get": {
                        "operationId": "get_diagram_set",
                        "responses": {"200": {
                            "description": "Diagram set",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                            "links": {"diagrams": {
                                "operationId": "list_diagram_set_diagrams",
                                "parameters": {
                                    "path.diagram_set_id": "$response.body#/diagram_set_id"
                                },
                                "x-sirenity": {"rel": "collection", "scope": "collection"},
                            }},
                        }},
                    },
                },
                "/diagram-sets/{diagram_set_id}/diagrams": {
                    "parameters": [{
                        "name": "diagram_set_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }],
                    "get": {
                        "operationId": "list_diagram_set_diagrams",
                        "responses": {"200": {
                            "description": "Diagrams",
                            "content": {"application/json": {"schema": {
                                "type": "array", "items": {"type": "object"}
                            }}},
                        }},
                    },
                },
            },
        }

        document = siren(schema).project_response(SirenResponseContext(
            operation_id="get_diagram_set",
            status=200,
            result={"diagram_set_id": "set-7"},
            base_url="https://api.example.com",
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/diagram-sets/set-7"},
            {
                "rel": ["collection"],
                "href": "https://api.example.com/diagram-sets/set-7/diagrams",
            },
        ]

    def test_public_engine_rejects_invalid_openapi_response_link_targets_at_startup(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/articles/{article_key}"]["get"]["responses"]["200"]["links"] = {
            "article": {
                "operationId": "get_article",
                "parameters": {},
                "x-sirenity": {"rel": "canonical", "scope": "entity"},
            }
        }

        with pytest.raises(SirenContractError) as raised:
            siren(schema)

        assert raised.value.location == "#"
        assert raised.value.category == "compilation"
        assert raised.value.detail == "OpenAPI response link parameters do not match the target route"

    def test_public_engine_explains_ambiguous_response_link_targets(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/articles/{article_key}"]["get"]["responses"]["200"]["links"] = {
            "article": {
                "operationId": "get_article",
                "operationRef": "#/paths/~1articles~1{article_key}/get",
                "parameters": {"article_key": "$response.body#/article_key"},
                "x-sirenity": {"rel": "canonical", "scope": "entity"},
            }
        }

        with pytest.raises(SirenContractError) as raised:
            siren(schema)

        assert raised.value.location == "#"
        assert raised.value.category == "openapi"
        assert raised.value.detail == "OpenAPI document does not conform to OpenAPI 3.1."

    def test_public_engine_projects_collection_owned_object_responses_as_entities(self):
        engine = siren(self.schema)
        context = SirenResponseContext(
            operation_id="create_article",
            status=201,
            result={"article_key": "created", "title": "Created"},
            base_url="https://api.example.com",
        )

        document = engine.project_response(context).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        assert document["class"] == ["article"]
        assert document["properties"] == {
            "article_key": "created", "title": "Created"}
        assert document["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/articles/created"}
        ]

    def test_public_engine_derives_entity_responses_without_an_identifier_heuristic(self):
        document = siren(self.schema).project_response(SirenResponseContext(
            operation_id="update_article",
            status=200,
            result={"article_key": "alternate", "title": "Updated"},
            base_url="https://api.example.com",
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["class"] == ["article"]
        assert document["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/articles/alternate"}
        ]

    def test_public_engine_projects_command_results_without_resource_masquerading(self):
        engine = siren(self.schema)
        publication_context = SirenResponseContext(
            operation_id="publish_article",
            status=202,
            result={"published": True},
            base_url="https://api.example.com",
            path_values={"article_key": "article/42"},
        )
        publication = engine.project_response(publication_context).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        reindex = engine.project_response(SirenResponseContext(
            operation_id="reindex",
            status=202,
            result={"accepted": True},
            base_url="https://api.example.com",
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert publication == {
            "class": ["command-result"],
            "properties": {"published": True},
            "links": [
                {"rel": [
                    "self"], "href": "https://api.example.com/articles/article%2F42/publish"}
            ],
        }
        assert reindex == {
            "class": ["command-result"],
            "properties": {"accepted": True},
            "links": [{"rel": ["self"], "href": "https://api.example.com/maintenance/reindex"}],
        }

    def test_public_engine_projects_empty_and_structured_error_outcomes(self):
        engine = siren(self.schema)
        empty = engine.project_response(SirenResponseContext(
            operation_id="delete_article",
            status=204,
            base_url="https://api.example.com",
            path_values={"article_key": "removed"},
        )).model_dump(by_alias=True, mode="json", exclude_none=True)
        error = engine.project_response(SirenResponseContext(
            operation_id="get_article",
            status=404,
            media_type="application/problem+json",
            result={"detail": "Article was not found"},
            base_url="https://api.example.com",
            path_values={"article_key": "missing"},
        )).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert empty == {
            "class": ["empty"],
            "properties": {"status": 204},
            "links": [{"rel": ["self"], "href": "https://api.example.com/articles/removed"}],
        }
        assert error == {
            "class": ["error"],
            "properties": {"detail": "Article was not found", "status": 404},
            "links": [{"rel": ["self"], "href": "https://api.example.com/articles/missing"}],
        }

    def test_public_engine_rejects_undeclared_statuses_and_runtime_shape_mismatches(self):
        engine = siren(self.schema)
        with pytest.raises(SirenityError, match="Siren response projection failed"):
            engine.project_response(SirenResponseContext(
                operation_id="list_articles",
                status=201,
                result=[],
                base_url="https://api.example.com",
            ))
        with pytest.raises(SirenityError, match="Siren response projection failed"):
            engine.project_response(SirenResponseContext(
                operation_id="list_articles",
                status=200,
                result={"article_key": "not-a-list"},
                base_url="https://api.example.com",
            ))
