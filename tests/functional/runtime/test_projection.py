import pytest
from pydantic import ValidationError

from sirenity import (
    SirenContext,
    SirenDocument,
    SirenEmbeddedRepresentation,
    SirenityError,
    SirenRelationship,
    SirenResponseContext,
    SirenScope,
    siren,
)

from ..compiler.openapi_documents import SCHEMA


class TestProjection:
    def test_public_facade_projects_a_relationship_link(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Relationships", "version": "1"},
            "paths": {
                "/example_resources": {
                    "get": {
                        "operationId": "list_example_resources",
                        "summary": "List example resources",
                        "description": "List example resources.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/example_resources/{example_resource_id}": {
                    "parameters": [
                        {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "get": {
                        "operationId": "get_example_resource",
                        "summary": "Read example resource",
                        "description": "Read an example resource.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/users/{user_id}": {
                    "parameters": [{"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "get": {
                        "operationId": "get_user",
                        "summary": "Read user",
                        "description": "Read a user.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
            },
        }

        engine = siren(schema)
        document = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                value={"example_resource_id": "42"},
                relationships=(
                SirenRelationship(
                    rel=("https://example.com/rels/example-owner",),
                    resource="user",
                    scope=SirenScope.ENTITY,
                    value={"user_id": "7"},
                ),
                ),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/example_resources/42"},
            {"rel": ["https://example.com/rels/example-owner"], "href": "https://api.example.com/users/7"},
        ]

        collection = (
            siren(schema)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="collection",
                    resource="example_resource",
                    items=({"example_resource_id": "42"},),
                    relationships=(
                        SirenRelationship(
                            rel=("related",), resource="user", scope=SirenScope.ENTITY, value={"user_id": "7"}
                        ),
                    ),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert collection["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/example_resources"},
            {"rel": ["related"], "href": "https://api.example.com/users/7"},
        ]

    def test_public_facade_projects_a_nested_collection_relationship(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Relationships", "version": "1"},
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
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/diagrams": {
                    "get": {
                        "operationId": "list_diagrams",
                        "summary": "List diagrams",
                        "description": "List diagrams.",
                        "responses": {"200": {"description": "OK"}},
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
                                "description": "OK",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "title": "Diagrams",
                                            "items": {"type": "object", "title": "Diagram"},
                                        },
                                    }
                                },
                            }
                        },
                    },
                },
            },
        }

        engine = siren(schema)
        document = engine.project(
            SirenContext(
                base_url="https://api.example.com",
                resource="diagram_set",
                value={"diagram_set_id": "set-7"},
                relationships=(
                    SirenRelationship(
                        rel=("collection",),
                        resource="diagram",
                        scope=SirenScope.COLLECTION,
                        path_values={"diagram_set_id": "set-7"},
                        capabilities=frozenset({"list_diagram_set_diagrams"}),
                    ),
                ),
            )
        ).model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {"rel": ["self"], "href": "https://api.example.com/diagram-sets/set-7"},
            {
                "rel": ["collection"],
                "title": "Diagrams",
                "href": "https://api.example.com/diagram-sets/set-7/diagrams",
            },
        ]

        with pytest.raises(SirenityError, match="Siren projection failed"):
            engine.project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="diagram_set",
                    value={"diagram_set_id": "set-7"},
                    relationships=(
                        SirenRelationship(
                            rel=("collection",),
                            resource="diagram",
                            scope=SirenScope.ENTITY,
                            path_values={"diagram_set_id": "set-7"},
                            capabilities=frozenset({"list_diagram_set_diagrams"}),
                        ),
                    ),
                )
            )

    def test_public_facade_rejects_invalid_collection_relationships(self):
        with pytest.raises(ValidationError, match="scope"):
            SirenRelationship(rel=("collection",), resource="diagram")
        with pytest.raises(SirenityError, match="Siren collection relationships cannot be embedded"):
            SirenRelationship(rel=("collection",), resource="diagram", scope=SirenScope.COLLECTION, embedded=True)
        with pytest.raises(SirenityError, match="Siren relationship scope must be entity or collection"):
            SirenRelationship(rel=("collection",), resource="diagram", scope=SirenScope.ROOT)

    def test_public_facade_requires_nested_collection_relationship_path_values(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Relationships", "version": "1"},
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
                        "responses": {"200": {"description": "OK"}},
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
                        "responses": {"200": {"description": "OK"}},
                    },
                },
            },
        }

        with pytest.raises(SirenityError, match="Siren projection failed: Siren link requires path value"):
            siren(schema).project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="diagram_set",
                    value={"diagram_set_id": "set-7"},
                    relationships=(
                        SirenRelationship(rel=("collection",), resource="diagram", scope=SirenScope.COLLECTION),
                    ),
                )
            )

    def test_public_facade_projects_an_embedded_relationship_representation(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Relationships", "version": "1"},
            "paths": {
                "/example_resources/{example_resource_id}": {
                    "parameters": [
                        {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "get": {
                        "operationId": "get_example_resource",
                        "summary": "Read example resource",
                        "description": "Read an example resource.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/users/{user_id}": {
                    "parameters": [{"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "get": {
                        "operationId": "get_user",
                        "summary": "Read user",
                        "description": "Read a user.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
            },
        }

        document = (
            siren(schema)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="example_resource",
                    value={"example_resource_id": "42"},
                    relationships=(
                        SirenRelationship(
                            rel=("https://example.com/rels/example-owner",),
                            resource="user",
                            scope=SirenScope.ENTITY,
                            value={"user_id": "7", "name": "Ada"},
                            capabilities=frozenset({"get_user"}),
                            embedded=True,
                        ),
                    ),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert document["entities"] == [
            {
                "class": ["user"],
                "rel": ["https://example.com/rels/example-owner"],
                "properties": {"user_id": "7", "name": "Ada"},
                "actions": [
                    {
                        "name": "get_user",
                        "href": "https://api.example.com/users/7",
                        "method": "GET",
                        "title": "Read user",
                    }
                ],
                "links": [{"rel": ["self"], "href": "https://api.example.com/users/7"}],
            }
        ]

    def test_public_facade_rejects_an_unknown_relationship_resource(self):
        with pytest.raises(SirenityError, match="Siren projection failed"):
            siren(SCHEMA).project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="example_resource",
                    value={"id": "42"},
                    relationships=(
                SirenRelationship(
                    rel=("https://example.com/rels/example-owner",),
                    resource="user",
                    scope=SirenScope.ENTITY,
                    value={"id": "7"},
                ),
                    ),
                )
            )

    def test_engine_rejects_a_capability_outside_the_resource_contract(self):
        with pytest.raises(SirenityError, match="Siren projection failed"):
            siren(SCHEMA).project(
                SirenContext(
                    base_url="https://api.example.com",
                    resource="example_resource",
                    value={"id": "42"},
                    capabilities=frozenset({"archive_example_resource"}),
                )
            )

    def test_public_facade_projects_collection_items_as_embedded_representations(self):
        document = siren(SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                items=({"id": "42", "title": "Architecture"},),
                capabilities=frozenset({"list_example_resources", "get_example_resource"}),
            )
        )

        assert isinstance(document, SirenDocument)
        assert isinstance(document.entities[0], SirenEmbeddedRepresentation)
        assert document.model_dump(by_alias=True, mode="json", exclude_none=True)["entities"] == [
            {
                "class": ["example-resource"],
                "title": "Architecture",
                "rel": ["item"],
                "properties": {"id": "42", "title": "Architecture"},
                "actions": [
                    {
                        "name": "get_example_resource",
                        "href": "https://api.example.com/example_resources/42",
                        "method": "GET",
                    "title": "Read example resource",
                    }
                ],
                "links": [
                    {
                        "title": "Architecture",
                        "rel": ["self"],
                        "href": "https://api.example.com/example_resources/42",
                    }
                ],
            }
        ]

    def test_public_facade_projects_item_specific_capabilities(self):
        document = (
            siren(SCHEMA)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="collection",
                    resource="example_resource",
                    items=(
                        {"id": "42", "title": "Draft"},
                        {"id": "43", "title": "Published"},
                    ),
                    capabilities=frozenset({"list_example_resources"}),
                    item_capabilities=(
                        frozenset({"get_example_resource", "rename_example_resource"}),
                        frozenset({"get_example_resource"}),
                    ),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )

        assert [[action["name"] for action in item["actions"]] for item in document["entities"]] == [
            ["get_example_resource", "rename_example_resource"],
            ["get_example_resource"],
        ]

    def test_public_facade_rejects_misaligned_item_capabilities(self):
        with pytest.raises(SirenityError, match="Siren item capabilities must align with collection items"):
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                items=({"id": "42"},),
                item_capabilities=(frozenset({"get_example_resource"}), frozenset({"rename_example_resource"})),
            )

    def test_public_facade_validates_item_title_alignment_and_allows_empty_collections(self):
        with pytest.raises(SirenityError, match="Siren item titles must align with collection items"):
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                items=({"id": "42"},),
                item_titles=("First", "Second"),
            )

        context = SirenResponseContext(
            operation_id="list_example_resources",
            status=200,
            result=[],
            base_url="https://api.example.com",
            item_titles=(),
        )

        assert context.item_titles == ()

    def test_response_context_rejects_misaligned_item_titles(self):
        with pytest.raises(SirenityError, match="Siren item titles must align with response items"):
            SirenResponseContext(
                operation_id="list_example_resources",
                status=200,
                result=[{"id": "42"}],
                base_url="https://api.example.com",
                item_titles=("First", "Second"),
            )

    def test_public_facade_projects_an_entity_with_concrete_links_and_allowed_actions(self):
        document = siren(SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                value={"id": "42", "title": "Architecture"},
                capabilities=frozenset({"get_example_resource", "rename_example_resource"}),
            )
        )

        assert isinstance(document, SirenDocument)
        payload = document.model_dump(by_alias=True, mode="json", exclude_none=True)
        assert payload["links"] == [{"rel": ["self"], "href": "https://api.example.com/example_resources/42"}]
        assert [action["name"] for action in payload["actions"]] == ["get_example_resource", "rename_example_resource"]
        assert payload["actions"][0] == {
            "name": "get_example_resource",
            "href": "https://api.example.com/example_resources/42",
            "method": "GET",
            "title": "Read example resource",
        }
        assert payload["actions"][1]["type"] == "application/json"
        assert payload["actions"][1]["fields"][0] == {"name": "title", "type": "text", "title": "Title"}

    def test_public_facade_projects_only_followable_root_links_and_eligible_root_actions(self):
        schema = {
            "openapi": "3.1.1",
            "info": {"title": "Root actions", "version": "1"},
            "paths": {
                "/example_resources": {
                    "get": {
                        "operationId": "list_example_resources",
                        "summary": "List example resources",
                        "description": "List example resources.",
                        "responses": {"200": {"description": "OK"}},
                    }
                },
                "/searches": {
                    "post": {
                        "operationId": "search_example_resources",
                        "summary": "Search example resources",
                        "description": "Search example resources.",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"phrase": {"type": "string", "title": "Phrase"}},
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "OK"}},
                    }
                },
                "/outboxes": {
                    "post": {
                        "operationId": "clear_outbox",
                        "summary": "Clear outbox",
                        "description": "Clear the outbox.",
                        "responses": {"204": {"description": "OK"}},
                    }
                },
                "/commands/rebuild": {
                    "post": {
                        "operationId": "rebuild_index",
                        "summary": "Rebuild index",
                        "description": "Rebuild the index.",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"scope": {"type": "string", "title": "Scope"}},
                                    }
                                }
                            }
                        },
                        "responses": {"202": {"description": "Accepted"}},
                    }
                },
                "/example_resources/{example_resource_id}": {
                    "parameters": [
                        {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "get": {
                        "operationId": "get_example_resource",
                        "summary": "Read example resource",
                        "description": "Read an example resource.",
                        "responses": {"200": {"description": "OK"}},
                    },
                },
                "/commands/{command_id}/run": {
                    "parameters": [
                        {"name": "command_id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "post": {
                        "operationId": "run_command",
                        "summary": "Run command",
                        "description": "Run a command.",
                        "responses": {"202": {"description": "Accepted"}},
                    },
                },
            },
        }

        document = siren(schema).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="root",
                path_values={"command_id": "command/42"},
                query=(("format", "siren"),),
                capabilities=frozenset(
                    {"search_example_resources", "rebuild_index", "get_example_resource", "run_command"}
                ),
            )
        )

        assert isinstance(document, SirenDocument)
        payload = document.model_dump(by_alias=True, mode="json", exclude_none=True)
        assert payload["links"] == [
            {"title": "Root actions", "rel": ["self"], "href": "https://api.example.com/?format=siren"},
            {"rel": ["collection"], "href": "https://api.example.com/example_resources"},
        ]
        assert payload["actions"] == [
            {
                "name": "search_example_resources",
                "href": "https://api.example.com/searches",
                "method": "POST",
                "title": "Search example resources",
                "type": "application/json",
                "fields": [{"name": "phrase", "type": "text", "title": "Phrase"}],
            },
            {
                "name": "rebuild_index",
                "href": "https://api.example.com/commands/rebuild",
                "method": "POST",
                "title": "Rebuild index",
                "type": "application/json",
                "fields": [{"name": "scope", "type": "text", "title": "Scope"}],
            },
            {
                "name": "run_command",
                "href": "https://api.example.com/commands/command%2F42/run",
                "method": "POST",
                "title": "Run command",
            },
        ]
