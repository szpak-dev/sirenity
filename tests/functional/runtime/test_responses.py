from copy import deepcopy
from typing import ClassVar

import pytest

from sirenity import SirenContractError, SirenityError, SirenResponseContext, siren


class TestResponses:
    schema: ClassVar[dict[str, object]] = {
        "openapi": "3.1.1",
        "info": {"title": "Response projection", "version": "1"},
        "paths": {
            "/example_resources": {
                "get": {
                    "operationId": "list_example_resources",
                    "summary": "List example resources",
                    "description": "List example resources.",
                    "responses": {
                        "200": {
                            "description": "Example resources.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "title": "Example resources",
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
                            "$ref": "#/components/responses/ExampleResourceCreated",
                        }
                    },
                },
            },
            "/example_resources/{example_resource_key}": {
                "parameters": [
                    {
                        "name": "example_resource_key",
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
                        },
                        "404": {
                            "description": "Missing example resource.",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Problem"}},
                                "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}},
                            },
                        },
                    },
                },
                "patch": {
                    "operationId": "update_example_resource",
                    "summary": "Update example resource",
                    "description": "Update an example resource.",
                    "responses": {
                        "200": {
                            "description": "Updated example resource.",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ExampleResource"}}
                            },
                        }
                    },
                },
                "delete": {
                    "operationId": "delete_example_resource",
                    "summary": "Delete example resource",
                    "description": "Delete an example resource.",
                    "responses": {"204": {"description": "Deleted"}},
                },
            },
            "/example_resources/{example_resource_key}/publish": {
                "parameters": [
                    {
                        "name": "example_resource_key",
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
                            "description": "Publication result",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/PublicationResult"}}
                            },
                        }
                    },
                },
            },
            "/maintenance/reindex": {
                "post": {
                    "operationId": "reindex",
                    "summary": "Reindex",
                    "description": "Reindex content.",
                    "responses": {
                        "202": {
                            "description": "Reindex result",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReindexResult"}}},
                        }
                    },
                }
            },
        },
        "components": {
            "responses": {
                "ExampleResourceCreated": {
                    "description": "Created example resource.",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExampleResource"}}},
                }
            },
            "schemas": {
                "ExampleResource": {
                    "type": "object",
                    "title": "Example resource",
                    "required": ["example_resource_key", "title"],
                    "properties": {
                        "example_resource_key": {"type": "string"},
                        "title": {"type": "string"},
                    },
                },
                "Problem": {
                    "type": "object",
                    "title": "Problem",
                    "required": ["detail"],
                    "properties": {"detail": {"type": "string"}},
                },
                "PublicationResult": {
                    "type": "object",
                    "title": "Publication result",
                    "properties": {"published": {"type": "boolean"}},
                },
                "ReindexResult": {
                    "type": "object",
                    "title": "Reindex result",
                    "properties": {"accepted": {"type": "boolean"}},
                },
            },
        },
    }

    def test_public_engine_projects_declared_array_responses_as_collections(self):
        document = (
            siren(self.schema)
            .project_response(
                SirenResponseContext(
                    operation_id="list_example_resources",
                    status=200,
                    result=[{"example_resource_key": "first", "title": "First"}],
                    base_url="https://api.example.com",
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert document == {
            "class": ["collection", "example-resource"],
            "title": "Example resource",
            "properties": {},
            "entities": [
                {
                    "class": ["example-resource"],
                    "title": "First",
                    "rel": ["item"],
                    "properties": {"example_resource_key": "first", "title": "First"},
                    "links": [
                        {
                            "title": "First",
                            "rel": ["self"],
                            "href": "https://api.example.com/example_resources/first",
                        }
                    ],
                }
            ],
            "links": [
                {"title": "Example resource", "rel": ["self"], "href": "https://api.example.com/example_resources"}
            ],
        }

    def test_public_engine_binds_response_values_into_item_action_fields(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/example_resources/{example_resource_key}"]["patch"]["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "title": "Example resource update",
                        "properties": {
                            "title": {"type": "string", "title": "Title"},
                        },
                    }
                }
            }
        }
        schema["paths"]["/example_resources"]["get"]["responses"]["200"]["x-sirenity"] = {
            "actionBindings": {"update_example_resource": {"title": "$response.body#/title"}}
        }

        document = (
            siren(schema)
            .project_response(
                SirenResponseContext(
                    operation_id="list_example_resources",
                    status=200,
                    result=[{"example_resource_key": "first", "title": "Current"}],
                    base_url="https://api.example.com",
                    item_capabilities=(frozenset({"update_example_resource"}),),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert document["entities"][0]["actions"][0]["fields"] == [
            {"name": "title", "type": "text", "title": "Title", "value": "Current"}
        ]

    def test_public_engine_projects_openapi_response_links_without_runtime_relationship_policy(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/example_resources/{example_resource_key}"]["get"]["responses"]["200"]["links"] = {
            "example_resourceCollection": {
                "operationId": "list_example_resources",
                "x-sirenity": {"rel": "collection", "scope": "collection"},
            }
        }
        schema["paths"]["/example_resources/{example_resource_key}"]["patch"]["responses"]["200"]["links"] = {
            "example_resource": {
                "operationRef": "#/paths/~1example_resources~1{example_resource_key}/get",
                "parameters": {"path.example_resource_key": "$response.body#/example_resource_key"},
                "x-sirenity": {"rel": ["self", "canonical"], "scope": "entity"},
            }
        }

        entity = (
            siren(schema)
            .project_response(
                SirenResponseContext(
                    operation_id="get_example_resource",
                    status=200,
                    result={"example_resource_key": "42", "title": "Linked"},
                    base_url="https://api.example.com",
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )
        command = (
            siren(schema)
            .project_response(
                SirenResponseContext(
                    operation_id="update_example_resource",
                    status=200,
                    result={"example_resource_key": "42", "title": "Linked"},
                    base_url="https://api.example.com",
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert entity["links"] == [
            {"title": "Example resource", "rel": ["self"], "href": "https://api.example.com/example_resources/42"},
            {"title": "Example resource", "rel": ["collection"], "href": "https://api.example.com/example_resources"},
        ]
        assert command["links"] == [
            {"title": "Example resource", "rel": ["self"], "href": "https://api.example.com/example_resources/42"},
            {
                "title": "Example resource",
                "rel": ["self", "canonical"],
                "href": "https://api.example.com/example_resources/42",
            },
        ]

    def test_public_engine_rejects_invalid_openapi_response_link_bindings(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/example_resources/{example_resource_key}"]["get"]["responses"]["200"]["links"] = {
            "example_resource": {
                "operationId": "get_example_resource",
                "parameters": {"example_resource_key": "$response.body#/missing"},
                "x-sirenity": {"rel": "canonical", "scope": "entity"},
            }
        }

        with pytest.raises(SirenityError, match="Siren response projection failed"):
            siren(schema).project_response(
                SirenResponseContext(
                    operation_id="get_example_resource",
                    status=200,
                    result={"example_resource_key": "42", "title": "Linked"},
                    base_url="https://api.example.com",
                )
            )

    def test_public_engine_projects_a_nested_collection_response_link(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Diagram sets", "version": "1"},
            "paths": {
                "/diagram-sets/{diagram_set_id}": {
                    "parameters": [
                        {
                            "name": "diagram_set_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_diagram_set",
                        "summary": "Read diagram set",
                        "description": "Read a diagram set.",
                        "responses": {
                            "200": {
                                "description": "Diagram set",
                                "content": {"application/json": {"schema": {"type": "object", "title": "Diagram set"}}},
                                "links": {
                                    "diagrams": {
                                        "operationId": "list_diagram_set_diagrams",
                                        "parameters": {"path.diagram_set_id": "$response.body#/diagram_set_id"},
                                        "x-sirenity": {"rel": "collection", "scope": "collection"},
                                    }
                                },
                            }
                        },
                    },
                },
                "/diagram-sets/{diagram_set_id}/diagrams": {
                    "parameters": [
                        {
                            "name": "diagram_set_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "list_diagram_set_diagrams",
                        "summary": "List diagram set diagrams",
                        "description": "List diagrams in a diagram set.",
                        "responses": {
                            "200": {
                                "description": "Diagrams",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "title": "Diagrams",
                                            "items": {"type": "object", "title": "Diagram"},
                                        }
                                    }
                                },
                            }
                        },
                    },
                },
            },
        }

        document = (
            siren(schema)
            .project_response(
                SirenResponseContext(
                    operation_id="get_diagram_set",
                    status=200,
                    result={"diagram_set_id": "set-7"},
                    base_url="https://api.example.com",
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert document["links"] == [
            {"title": "Diagram set", "rel": ["self"], "href": "https://api.example.com/diagram-sets/set-7"},
            {
                "title": "Diagram",
                "rel": ["collection"],
                "href": "https://api.example.com/diagram-sets/set-7/diagrams",
            },
        ]

    def test_public_engine_rejects_invalid_openapi_response_link_targets_at_startup(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/example_resources/{example_resource_key}"]["get"]["responses"]["200"]["links"] = {
            "example_resource": {
                "operationId": "get_example_resource",
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
        schema["paths"]["/example_resources/{example_resource_key}"]["get"]["responses"]["200"]["links"] = {
            "example_resource": {
                "operationId": "get_example_resource",
                "operationRef": "#/paths/~1example_resources~1{example_resource_key}/get",
                "parameters": {"example_resource_key": "$response.body#/example_resource_key"},
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
            operation_id="create_example_resource",
            status=201,
            result={"example_resource_key": "created", "title": "Created"},
            base_url="https://api.example.com",
        )

        document = engine.project_response(context).model_dump(by_alias=True, mode="json", exclude_none=True)
        assert document["class"] == ["example-resource"]
        assert document["properties"] == {"example_resource_key": "created", "title": "Created"}
        assert document["links"] == [
            {"title": "Example resource", "rel": ["self"], "href": "https://api.example.com/example_resources/created"}
        ]

    def test_public_engine_derives_entity_responses_without_an_identifier_heuristic(self):
        document = (
            siren(self.schema)
            .project_response(
                SirenResponseContext(
                    operation_id="update_example_resource",
                    status=200,
                    result={"example_resource_key": "alternate", "title": "Updated"},
                    base_url="https://api.example.com",
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert document["class"] == ["example-resource"]
        assert document["links"] == [
            {"title": "Example resource", "rel": ["self"], "href": "https://api.example.com/example_resources/alternate"}
        ]

    def test_public_engine_projects_command_results_without_resource_masquerading(self):
        engine = siren(self.schema)
        publication_context = SirenResponseContext(
            operation_id="publish_example_resource",
            status=202,
            result={"published": True},
            base_url="https://api.example.com",
            path_values={"example_resource_key": "example_resource/42"},
        )
        publication = engine.project_response(publication_context).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        reindex = engine.project_response(
            SirenResponseContext(
                operation_id="reindex",
                status=202,
                result={"accepted": True},
                base_url="https://api.example.com",
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert publication == {
            "class": ["command-result"],
            "title": "Publish example resource",
            "properties": {"published": True},
            "links": [
                {
                    "title": "Publish example resource",
                    "rel": ["self"],
                    "href": "https://api.example.com/example_resources/example_resource%2F42/publish",
                }
            ],
        }
        assert reindex == {
            "class": ["command-result"],
            "title": "Reindex",
            "properties": {"accepted": True},
            "links": [{"title": "Reindex", "rel": ["self"], "href": "https://api.example.com/maintenance/reindex"}],
        }

    def test_public_engine_projects_empty_and_structured_error_outcomes(self):
        engine = siren(self.schema)
        empty = engine.project_response(
            SirenResponseContext(
                operation_id="delete_example_resource",
                status=204,
                base_url="https://api.example.com",
                path_values={"example_resource_key": "removed"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        error = engine.project_response(
            SirenResponseContext(
                operation_id="get_example_resource",
                status=404,
                media_type="application/problem+json",
                result={"detail": "ExampleResource was not found"},
                base_url="https://api.example.com",
                path_values={"example_resource_key": "missing"},
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert empty == {
            "class": ["empty"],
            "title": "Delete example resource",
            "properties": {"status": 204},
            "links": [
                {
                    "title": "Delete example resource",
                    "rel": ["self"],
                    "href": "https://api.example.com/example_resources/removed",
                }
            ],
        }
        assert error == {
            "class": ["error"],
            "title": "Read example resource",
            "properties": {"detail": "ExampleResource was not found", "status": 404},
            "links": [
                {
                    "title": "Read example resource",
                    "rel": ["self"],
                    "href": "https://api.example.com/example_resources/missing",
                }
            ],
        }

    def test_public_engine_rejects_undeclared_statuses_and_runtime_shape_mismatches(self):
        engine = siren(self.schema)
        with pytest.raises(SirenityError, match="Siren response projection failed"):
            engine.project_response(
                SirenResponseContext(
                    operation_id="list_example_resources",
                    status=201,
                    result=[],
                    base_url="https://api.example.com",
                )
            )
        with pytest.raises(SirenityError, match="Siren response projection failed"):
            engine.project_response(
                SirenResponseContext(
                    operation_id="list_example_resources",
                    status=200,
                    result={"example_resource_key": "not-a-list"},
                    base_url="https://api.example.com",
                )
            )
