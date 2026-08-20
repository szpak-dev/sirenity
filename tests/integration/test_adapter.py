import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
from typing import ClassVar

import pytest
from django.conf import settings
from django.core.handlers.base import BaseHandler
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
)
from django.test import RequestFactory, override_settings

from sirenity import (
    SirenAdapter,
    SirenAdapterPolicy,
    SirenAdapterRequest,
    SirenAllowAllPolicy,
    SirenConfiguration,
    SirenDelegatedInput,
    SirenDjangoMiddleware,
    SirenInput,
    SirenityError,
    SirenMiddleware,
    SirenResponseContext,
    SirenStructuredFormProfile,
    siren_adapter,
    siren_configuration,
)

from ..framework_fixtures.capability_policy import CapabilityPolicy
from ..framework_fixtures.django_openapi_provider import django_openapi_provider
from ..framework_fixtures.root_capability_policy import RootCapabilityPolicy


class TestAdapter:
    schema: ClassVar[dict[str, object]] = {
        "openapi": "3.1.1",
        "info": {"title": "Adapter API", "version": "4.0.0"},
        "paths": {
            "/api": {
                "get": {
                    "operationId": "get_api_root",
                    "summary": "Read API entry point",
                    "description": "Read the API entry point.",
                    "responses": {
                        "200": {
                            "description": "API entry point",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "API entry point",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "version": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/reindex": {
                "post": {
                    "operationId": "reindex",
                    "summary": "Reindex content",
                    "description": "Request content reindexing.",
                    "responses": {
                        "202": {
                            "description": "Reindex accepted",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "Reindex result",
                                        "properties": {"accepted": {"type": "boolean"}},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/example_resources": {
                "get": {
                    "operationId": "list_example_resources",
                    "summary": "List example resources",
                    "description": "List available example resources.",
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
                        },
                        "default": {
                            "description": "List failure",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Problem"}}},
                        },
                    },
                }
            },
            "/api/example_resources/{example_resource_key}": {
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
                    "description": "Read one example resource.",
                    "responses": {
                        "200": {
                            "description": "Example resource.",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/ExampleResource"}}
                            },
                        },
                    },
                },
                "delete": {
                    "operationId": "delete_example_resource",
                    "summary": "Delete example resource",
                    "description": "Delete one example resource.",
                    "responses": {
                        "204": {"description": "Deleted"},
                        "404": {
                            "description": "Missing",
                            "content": {
                                "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}
                            },
                        },
                    },
                },
            },
            "/api/example_resources/{example_resource_key}/publish": {
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
                    "description": "Publish one example resource.",
                    "responses": {
                        "202": {
                            "description": "Published",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "Publication",
                                        "properties": {"published": {"type": "boolean"}},
                                    }
                                }
                            },
                        },
                        "4XX": {
                            "description": "Publish failure",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Problem"}}},
                        },
                    },
                },
            },
        },
        "components": {
            "schemas": {
                "ExampleResource": {
                    "type": "object",
                    "title": "Example resource",
                    "properties": {
                        "example_resource_key": {"type": "string"},
                        "title": {"type": "string"},
                    },
                },
                "Problem": {
                    "type": "object",
                    "title": "Problem",
                    "properties": {"detail": {"type": "string"}},
                },
            }
        },
    }

    def test_public_adapter_routes_expose_compiled_source_and_public_mounts(self):
        routes = {route.operation_id: route for route in siren_adapter(self.schema).routes}

        assert routes["get_api_root"].source_path == "/api"
        assert routes["get_api_root"].public_path == "/api"

    def test_framework_neutral_boundary_resolves_mounts_and_projects_every_outcome(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")

        source = adapter.match("GET", "/api/example_resources/a%2Fb")
        public = adapter.match("GET", "/siren/example_resources/a%2Fb")
        assert source == public
        assert source.operation_id == "get_example_resource"
        assert source.path_values == {"example_resource_key": "a/b"}

        collection = adapter.respond(
            SirenAdapterRequest(
                method="GET",
                path="/api/example_resources",
                status=200,
                result=[{"example_resource_key": "one", "title": "One"}],
                base_url="https://example.test",
            )
        )
        entity = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_resource",
                status=200,
                result={"example_resource_key": "one", "title": "One"},
                base_url="https://example.test",
                headers={"ETag": "one", "Content-Type": "application/json", "Content-Length": "2"},
                policy=SirenAdapterPolicy(capabilities=frozenset({"get_example_resource"})),
            )
        )
        command = adapter.respond(
            SirenAdapterRequest(
                method="POST",
                path="/api/example_resources/one/publish",
                status=202,
                result={"published": True},
                base_url="https://example.test",
                policy=SirenAdapterPolicy(representation="command"),
            )
        )
        empty = adapter.respond(
            SirenAdapterRequest(
                method="DELETE",
                path="/api/example_resources/one",
                status=204,
                base_url="https://example.test",
            )
        )
        validation = adapter.respond(
            SirenAdapterRequest(
                method="GET",
                path="/api/example_resources/invalid",
                status=422,
                result=[{"location": "example_resource_key", "message": "Invalid"}],
                base_url="https://example.test",
            )
        )
        not_found = adapter.respond(
            SirenAdapterRequest(
                method="GET",
                path="/api/example_resources/missing",
                status=404,
                result={"detail": "Not found"},
                base_url="https://example.test",
            )
        )
        unmatched = adapter.respond(
            SirenAdapterRequest(
                method="GET",
                path="/api/unknown",
                status=404,
                result={"detail": "Not found"},
                base_url="https://example.test",
                request_url="https://example.test/api/unknown",
            )
        )

        assert collection.payload["class"] == ["collection", "example-resource"]
        assert entity.payload["class"] == ["example-resource"]
        assert entity.media_type == "application/vnd.siren+json"
        assert entity.headers == {}
        assert command.payload["class"] == ["command-result"]
        assert empty.payload["class"] == ["empty"]
        assert validation.payload["class"] == ["error"]
        assert validation.payload["properties"] == {
            "errors": [{"location": "example_resource_key", "message": "Invalid"}],
            "status": 422,
        }
        assert not_found.payload == {
            "class": ["error"],
            "title": "Read example resource",
            "properties": {"detail": "Not found", "status": 404},
            "links": [
                {
                    "title": "Read example resource",
                    "rel": ["self"],
                    "href": "https://example.test/siren/example_resources/missing",
                }
            ],
        }
        assert unmatched.payload == {
            "class": ["error"],
            "properties": {"detail": "Not found", "status": 404},
            "links": [{"rel": ["self"], "href": "https://example.test/api/unknown"}],
        }

    def test_allow_all_policy_derives_resource_capabilities_from_the_compiled_graph(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")
        policy = SirenAllowAllPolicy().select("get_example_resource", 200, object(), {})

        response = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_resource",
                status=200,
                result={"example_resource_key": "one", "title": "One"},
                base_url="https://example.test",
                policy=policy,
            )
        )

        assert {action["name"] for action in response.payload["actions"]} == {
            "delete_example_resource",
            "get_example_resource",
            "publish_example_resource",
        }

        collection = adapter.respond(
            SirenAdapterRequest(
                operation_id="list_example_resources",
                status=200,
                result=[{"example_resource_key": "one", "title": "One"}],
                base_url="https://example.test",
                policy=policy,
            )
        )
        root = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_api_root",
                status=200,
                result={"status": "ready"},
                base_url="https://example.test",
                policy=policy,
            )
        )

        assert {action["name"] for action in collection.payload["actions"]} == {
            "list_example_resources",
        }
        assert {action["name"] for action in collection.payload["entities"][0]["actions"]} == {
            "delete_example_resource",
            "get_example_resource",
            "publish_example_resource",
        }
        assert root.payload["class"] == ["api", "entry-point"]
        assert {action["name"] for action in root.payload["actions"]} == {
            "get_api_root",
            "reindex",
        }

    def test_adapter_policy_rejects_conflicting_capability_modes(self):
        with pytest.raises(
            SirenityError,
            match="cannot combine all capabilities with explicit capabilities",
        ):
            SirenAdapterPolicy(
                all_capabilities=True,
                capabilities=frozenset({"get_example_resource"}),
            )

    def test_adapter_policy_projects_distinct_aligned_collection_item_titles(self):
        response = siren_adapter(self.schema, source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                operation_id="list_example_resources",
                status=200,
                result=[
                    {"example_resource_key": "one", "title": "Stored one"},
                    {"example_resource_key": "two", "title": "Stored two"},
                ],
                base_url="https://example.test",
                policy=SirenAdapterPolicy(
                    item_titles=("First example_resource", "Second example_resource"),
                    item_capabilities=(
                        frozenset({"get_example_resource"}),
                        frozenset(),
                    ),
                ),
            )
        )

        assert [item["title"] for item in response.payload["entities"]] == [
            "First example_resource",
            "Second example_resource",
        ]
        assert [item["links"][0]["title"] for item in response.payload["entities"]] == [
            "First example_resource",
            "Second example_resource",
        ]
        assert [item.get("actions", []) for item in response.payload["entities"]] == [
            [
                {
                    "name": "get_example_resource",
                    "href": "https://example.test/siren/example_resources/one",
                    "method": "GET",
                    "title": "Read example resource",
                }
            ],
            [],
        ]

    def test_adapter_route_resolution_is_specific_deterministic_and_mount_independent(self):
        parameter_paths = {
            "/api/items/{item_id}": {
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "get": {
                    "operationId": "get_item",
                    "summary": "Read item",
                    "description": "Read one item.",
                    "responses": {"204": {"description": "Item"}},
                },
            },
            "/api/items/{item_id}/commands/{command_name}": {
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "command_name",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "post": {
                    "operationId": "run_item_command",
                    "summary": "Run item command",
                    "description": "Run one item command.",
                    "responses": {"204": {"description": "Command"}},
                },
            },
        }
        literal_paths = {
            "/api/items/search": {
                "get": {
                    "operationId": "search_items",
                    "summary": "Search items",
                    "description": "Search items.",
                    "responses": {"204": {"description": "Search"}},
                }
            },
            "/api/items/{item_id}/commands/retry": {
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "post": {
                    "operationId": "retry_item",
                    "summary": "Retry item",
                    "description": "Retry one item.",
                    "responses": {"204": {"description": "Retry"}},
                },
            },
        }

        for paths in (
            parameter_paths | literal_paths,
            literal_paths | parameter_paths,
        ):
            adapter = siren_adapter(
                {
                    "openapi": "3.1.1",
                    "info": {"title": "Routes", "version": "4.0.0"},
                    "paths": paths,
                },
                source_path="/api",
                public_path="/siren",
            )

            assert adapter.match("get", "/api/items/search/").operation_id == "search_items"
            assert adapter.match("GET", "/siren/items/search").operation_id == "search_items"
            encoded = adapter.match("GET", "/api/items/%73earch")
            assert encoded.operation_id == "get_item"
            assert encoded.path_values == {"item_id": "search"}
            nested = adapter.match("post", "/siren/items/one/commands/retry/")
            assert nested.operation_id == "retry_item"
            assert nested.path_values == {"item_id": "one"}
            generic = adapter.match("POST", "/api/items/one/commands/archive")
            assert generic.operation_id == "run_item_command"
            assert generic.path_values == {"item_id": "one", "command_name": "archive"}
            assert adapter.match("DELETE", "/api/items/search") is None

    def test_adapter_construction_rejects_indistinguishable_route_templates(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")

        with pytest.raises(
            SirenityError,
            match=r"Ambiguous Siren adapter templates for GET /api/items/\{\}",
        ):
            SirenAdapter(
                engine=adapter.engine,
                routes=(
                    {
                        "source_path": "/api/items/{item_id}",
                        "public_path": "/siren/items/{item_id}",
                        "method": "GET",
                        "operation_id": "get_item",
                    },
                    {
                        "source_path": "/api/items/{slug}",
                        "public_path": "/siren/items/{slug}",
                        "method": "GET",
                        "operation_id": "get_item_by_slug",
                    },
                ),
            )

    def test_structured_form_profile_exposes_delegated_inputs_without_changing_default_siren(self):
        document = deepcopy(self.schema)
        document["components"]["schemas"].update(
            {
                "Filter": {
                    "type": "object",
                    "required": ["state"],
                    "properties": {"state": {"type": "string"}},
                },
                "Metadata": {
                    "type": "object",
                    "required": ["source"],
                    "properties": {"source": {"type": "string"}},
                    "additionalProperties": {},
                },
                "ExampleResourcePatch": {
                    "type": "object",
                    "required": [
                        "metadata",
                        "items",
                        "payload",
                        "content_schema",
                        "example_resource_ids",
                    ],
                    "properties": {
                        "title": {"type": "string", "title": "Title"},
                        "metadata": {"$ref": "#/components/schemas/Metadata"},
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Metadata"},
                        },
                        "payload": {"type": "object", "additionalProperties": True},
                        "content_schema": {"type": "object", "additionalProperties": {}},
                        "implicit_document": {"type": "object"},
                        "empty_document": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": {},
                        },
                        "typed_map": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                        "closed_document": {"type": "object", "additionalProperties": False},
                        "example_resource_ids": {
                            "type": "array",
                            "title": "Example resource IDs",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {"type": "string", "format": "uuid"},
                        },
                    },
                },
            }
        )
        document["components"]["requestBodies"] = {
            "ExampleResourcePatch": {
                "required": True,
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExampleResourcePatch"}}},
            }
        }
        document["paths"]["/api/example_resources/{example_resource_key}"]["patch"] = {
            "operationId": "update_example_resource",
            "summary": "Update example resource",
            "description": "Update one example resource.",
            "parameters": [
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
                {
                    "name": "trace",
                    "in": "header",
                    "required": True,
                    "schema": {"type": "string"},
                },
                {"name": "session", "in": "cookie", "schema": {"type": "string"}},
            ],
            "requestBody": {"$ref": "#/components/requestBodies/ExampleResourcePatch"},
            "responses": {
                "200": {
                    "description": "Updated",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExampleResource"}}},
                }
            },
        }
        request = SirenAdapterRequest(
            operation_id="get_example_resource",
            status=200,
            result={"example_resource_key": "one", "title": "One"},
            base_url="https://example.test",
            path_values={"example_resource_key": "one"},
            policy=SirenAdapterPolicy(capabilities=frozenset({"update_example_resource"})),
        )
        default = siren_adapter(document, source_path="/api", public_path="/siren")
        profiled = siren_adapter(
            document,
            source_path="/api",
            public_path="/siren",
            profiles=(SirenStructuredFormProfile(),),
        )

        default_action = default.respond(request).payload["actions"][0]
        profiled_payload = profiled.respond(request).payload
        action = profiled_payload["actions"][0]
        extension_name = SirenStructuredFormProfile.extension

        assert extension_name not in default_action
        assert {field["name"] for field in action["fields"]} == {"page", "title"}
        extension = action[extension_name]
        assert extension["version"] == "1"
        controls = {control["name"]: control for control in extension["controls"]}
        assert set(controls) == {
            "filter",
            "trace",
            "session",
            "metadata",
            "items",
            "payload",
            "content_schema",
            "implicit_document",
            "empty_document",
            "typed_map",
            "closed_document",
            "example_resource_ids",
        }
        assert controls["filter"] == {
            "name": "filter",
            "location": "query",
            "required": True,
            "control": SirenStructuredFormProfile.object_control,
            "schema": {
                "type": "object",
                "required": ["state"],
                "properties": {"state": {"type": "string"}},
            },
            "serialization": {
                "style": "deepObject",
                "explode": True,
                "allowReserved": True,
            },
        }
        assert controls["trace"]["location"] == "header"
        assert controls["session"]["location"] == "cookie"
        assert controls["metadata"]["control"] == SirenStructuredFormProfile.object_control
        assert controls["metadata"]["schema"]["additionalProperties"] == {}
        assert controls["metadata"]["required"] is True
        assert controls["metadata"]["mediaType"] == "application/json"
        assert controls["items"]["control"] == SirenStructuredFormProfile.array_control
        assert controls["items"]["schema"]["items"]["type"] == "object"
        assert controls["example_resource_ids"] == {
            "name": "example_resource_ids",
            "location": "body",
            "required": True,
            "control": SirenStructuredFormProfile.array_control,
            "schema": {
                "type": "array",
                "title": "Example resource IDs",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "format": "uuid"},
            },
            "mediaType": "application/json",
        }
        assert controls["payload"]["control"] == SirenStructuredFormProfile.json_control
        assert controls["content_schema"] == {
            "name": "content_schema",
            "location": "body",
            "required": True,
            "control": SirenStructuredFormProfile.json_control,
            "schema": {"type": "object", "additionalProperties": {}},
            "mediaType": "application/json",
        }
        assert controls["implicit_document"]["control"] == SirenStructuredFormProfile.json_control
        assert controls["implicit_document"]["schema"] == {"type": "object"}
        assert controls["empty_document"]["control"] == SirenStructuredFormProfile.json_control
        assert controls["empty_document"]["schema"] == {
            "type": "object",
            "properties": {},
            "additionalProperties": {},
        }
        assert controls["typed_map"]["control"] == SirenStructuredFormProfile.object_control
        assert controls["closed_document"]["control"] == SirenStructuredFormProfile.object_control
        assert "$ref" not in json.dumps(extension)

        with ThreadPoolExecutor(max_workers=4) as executor:
            payloads = tuple(executor.map(lambda _: profiled.respond(request).payload, range(8)))

        assert all(payload == profiled_payload for payload in payloads)

    def test_structured_form_profile_recurses_and_custom_profiles_cannot_mutate_engine_inputs(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")
        operation_input = adapter.engine.operation_input("get_example_resource")
        delegated = SirenInput(
            delegated_inputs=(
                SirenDelegatedInput(
                    name="payload",
                    location="body",
                    kind="object",
                    required=True,
                    media_type="application/json",
                    definition={"type": "object"},
                ),
            )
        )
        action = {
            "name": "update_example_resource",
            "href": "https://example.test/example_resources/one",
            "method": "PATCH",
        }
        nested_document = {
            "class": ["api", "entry-point"],
            "actions": [action],
            "entities": [
                {
                    "class": ["collection"],
                    "rel": ["collection"],
                    "actions": [action],
                    "entities": [
                        {
                            "class": ["example-resource"],
                            "rel": ["item"],
                            "actions": [action],
                        }
                    ],
                }
            ],
        }
        context = SirenResponseContext(
            operation_id="get_example_resource",
            status=200,
            result={"example_resource_key": "one"},
            base_url="https://example.test",
        )
        profile = SirenStructuredFormProfile()
        enriched = profile.apply(
            operation_id="get_example_resource",
            operation_input=operation_input,
            operation_inputs={"update_example_resource": delegated},
            document=nested_document,
            context=context,
        )

        assert profile.extension in enriched["actions"][0]
        assert profile.extension in enriched["entities"][0]["actions"][0]
        assert profile.extension in enriched["entities"][0]["entities"][0]["actions"][0]
        assert profile.extension not in action

        class MutatingProfile:
            def apply(
                self,
                operation_id,
                operation_input,
                operation_inputs,
                document,
                context,
            ):
                for value in operation_inputs.values():
                    if value is not None and value.definition is not None:
                        value.definition["mutated"] = True
                return dict(document) | {"custom-profile": True}

        schema = deepcopy(self.schema)
        schema["paths"]["/api/example_resources/{example_resource_key}"]["patch"] = {
            "operationId": "update_example_resource",
            "summary": "Update example resource",
            "description": "Update one example resource.",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"metadata": {"type": "object"}},
                        }
                    }
                }
            },
            "responses": {"204": {"description": "Updated"}},
        }
        custom = siren_adapter(
            schema,
            source_path="/api",
            public_path="/siren",
            profiles=(MutatingProfile(),),
        )
        response = custom.respond(
            SirenAdapterRequest(
                operation_id="get_example_resource",
                status=200,
                result={"example_resource_key": "one", "title": "One"},
                base_url="https://example.test",
                path_values={"example_resource_key": "one"},
            )
        )

        assert response.payload["custom-profile"] is True
        assert "mutated" not in custom.engine.operation_input("update_example_resource").definition

    def test_adapter_projects_api_entry_points_and_keeps_explicit_root_commands(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")

        root = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_api_root",
                status=200,
                result={"status": "ready", "version": "runtime"},
                base_url="https://example.test",
                query=(("view", "full"),),
                policy=SirenAdapterPolicy(
                    representation="root",
                    capabilities=frozenset({"reindex"}),
                ),
            )
        )
        command = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_api_root",
                status=200,
                result={"status": "ready"},
                base_url="https://example.test",
                policy=SirenAdapterPolicy(representation="command"),
            )
        )
        titled = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_api_root",
                status=200,
                result={"status": "ready"},
                base_url="https://example.test",
                policy=SirenAdapterPolicy(representation="root", title="Live API"),
            )
        )

        assert root.payload == {
            "class": ["api", "entry-point"],
            "title": "Adapter API",
            "properties": {"status": "ready", "version": "4.0.0"},
            "actions": [
                {
                    "name": "reindex",
                    "title": "Reindex content",
                    "href": "https://example.test/siren/reindex",
                    "method": "POST",
                }
            ],
            "links": [
                {
                    "title": "Adapter API",
                    "rel": ["self"],
                    "href": "https://example.test/siren?view=full",
                },
                {
                    "title": "Example resource",
                    "rel": ["collection"],
                    "href": "https://example.test/siren/example_resources",
                },
            ],
        }
        assert command.payload["class"] == ["command-result"]
        assert command.payload["links"] == [
            {
                "title": "Read API entry point",
                "rel": ["self"],
                "href": "https://example.test/siren",
            }
        ]
        assert titled.payload["title"] == "Live API"
        assert titled.payload["links"][0]["title"] == "Live API"

        with pytest.raises(SirenityError, match="Siren adapter response failed"):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id="get_example_resource",
                    status=200,
                    result={"example_resource_key": "one"},
                    base_url="https://example.test",
                    policy=SirenAdapterPolicy(representation="root"),
                )
            )

    def test_undeclared_errors_preserve_every_body_shape_and_operation_context(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")

        mapping = adapter.respond(
            SirenAdapterRequest(
                method="GET",
                path="/api/example_resources/missing",
                status=404,
                result={"detail": "Missing"},
                base_url="https://example.test",
                request_url="https://example.test/api/example_resources/missing?trace=yes",
            )
        )
        scalar = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_resource",
                status=401,
                result="Denied",
                base_url="https://example.test",
                path_values={"example_resource_key": "private"},
            )
        )
        empty = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_resource",
                status=500,
                base_url="https://example.test",
                path_values={"example_resource_key": "broken"},
                policy=SirenAdapterPolicy(title="Unavailable"),
            )
        )

        assert mapping.payload == {
            "class": ["error"],
            "title": "Read example resource",
            "properties": {"detail": "Missing", "status": 404},
            "links": [
                {
                    "title": "Read example resource",
                    "rel": ["self"],
                    "href": "https://example.test/api/example_resources/missing?trace=yes",
                }
            ],
        }
        assert scalar.payload["properties"] == {"status": 401, "result": "Denied"}
        assert scalar.payload["links"][0]["href"] == "https://example.test/siren/example_resources/private"
        assert empty.payload["title"] == "Unavailable"
        assert empty.payload["properties"] == {"status": 500}

    @pytest.mark.parametrize(
        ("operation_id", "status", "media_type"),
        [
            ("delete_example_resource", 404, "application/problem+json"),
            ("publish_example_resource", 409, "application/json"),
            ("list_example_resources", 503, "application/json"),
        ],
    )
    def test_declared_exact_ranged_and_default_errors_remain_strict(self, operation_id, status, media_type):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="Siren adapter response failed"):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id=operation_id,
                    status=status,
                    result="Declared object responses reject scalars",
                    base_url="https://example.test",
                    media_type=media_type,
                    path_values={"example_resource_key": "one"},
                )
            )

    def test_declared_status_with_an_incompatible_media_type_uses_generic_error(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")

        response = adapter.respond(
            SirenAdapterRequest(
                operation_id="delete_example_resource",
                status=404,
                result="Missing",
                base_url="https://example.test",
                media_type="application/json",
                path_values={"example_resource_key": "missing"},
            )
        )

        assert response.payload["properties"] == {"status": 404, "result": "Missing"}

    def test_successful_undeclared_responses_remain_strict(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")

        with pytest.raises(SirenityError, match="Siren adapter response failed"):
            adapter.respond(
                SirenAdapterRequest(
                    operation_id="get_example_resource",
                    status=201,
                    result={"example_resource_key": "one"},
                    base_url="https://example.test",
                )
            )

    def test_django_bridge_executes_once_and_preserves_unselected_json(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/api")
        calls = []
        original = JsonResponse({"example_resource_key": "one", "title": "One"}, headers={"ETag": "one"})

        def handler(request):
            calls.append(request.path)
            if request.method == "DELETE":
                return HttpResponse(status=204)
            if request.path.endswith("invalid"):
                return JsonResponse(
                    [{"location": "example_resource_key", "message": "Invalid"}], status=422, safe=False
                )
            return original

        policy = CapabilityPolicy()
        middleware = SirenDjangoMiddleware(get_response=handler, adapter=adapter, policy=policy)
        factory = RequestFactory()
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            ordinary = middleware(factory.get("/api/example_resources/one", HTTP_ACCEPT="application/json"))
            siren = middleware(
                factory.get(
                    "/api/example_resources/one?view=full&view=compact",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )
            validation = middleware(
                factory.get(
                    "/api/example_resources/invalid",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )
            empty = middleware(
                factory.delete(
                    "/api/example_resources/one",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )

        assert ordinary is original
        assert ordinary["Vary"] == "Accept"
        assert siren.status_code == 200
        assert siren["Content-Type"] == "application/vnd.siren+json"
        assert "ETag" not in siren
        assert siren["Vary"] == "Accept"
        assert json.loads(siren.content)["class"] == ["example-resource"]
        assert json.loads(validation.content)["properties"] == {
            "errors": [{"location": "example_resource_key", "message": "Invalid"}],
            "status": 422,
        }
        assert json.loads(empty.content)["class"] == ["empty"]
        assert calls == [
            "/api/example_resources/one",
            "/api/example_resources/one",
            "/api/example_resources/invalid",
            "/api/example_resources/one",
        ]
        assert policy.calls == [
            ("get_example_resource", 200),
            ("get_example_resource", 422),
            ("delete_example_resource", 204),
        ]

    @pytest.mark.parametrize(
        ("accept", "selected"),
        (
            ("application/vnd.siren+json;q=0, application/json", False),
            ("application/vnd.siren+json;q=0.8, application/json;q=0.9", False),
            ("application/*", False),
            ("*/*", False),
            ("", False),
            ("APPLICATION/VND.SIREN+JSON", True),
            ("application/*;q=0.8, application/vnd.siren+json;q=0.9", True),
            ("application/json;q=0.5, application/*;q=0.9", True),
            ("application/vnd.siren+json;q=0.8, application/json;q=0.8", True),
            ("application/json;q=0.8, application/vnd.siren+json;q=0.8", False),
            ("application/vnd.siren+json;q=0, */*;q=1", False),
        ),
    )
    def test_django_bridge_negotiates_quality_specificity_and_wildcards(self, accept, selected):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/api")
        original = JsonResponse({"example_resource_key": "one", "title": "One"})
        calls = []

        def handler(request):
            calls.append(request.path)
            return original

        middleware = SirenDjangoMiddleware(
            get_response=handler,
            adapter=adapter,
            policy=CapabilityPolicy(),
        )
        request = RequestFactory().get("/api/example_resources/one", HTTP_ACCEPT=accept)
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            response = middleware(request)

        assert (response["Content-Type"] == "application/vnd.siren+json") is selected
        assert (response is not original) is selected
        assert calls == ["/api/example_resources/one"]

    def test_django_bridge_replaces_representation_headers_and_preserves_semantics(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/api")
        original = JsonResponse(
            {"example_resource_key": "one", "title": "One"},
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "private",
                "Content-Digest": "sha-256=:source:",
                "Content-Encoding": "gzip",
                "Content-Length": "42",
                "Content-Range": "bytes 0-41/42",
                "Content-Security-Policy": "default-src 'none'",
                "Digest": "sha-256=source",
                "ETag": '"json"',
                "Last-Modified": "Wed, 05 Aug 2026 00:00:00 GMT",
                "Location": "/api/example_resources/one",
                "RateLimit-Limit": "100",
                "Vary": "Origin, Cookie",
                "WWW-Authenticate": 'Bearer realm="api"',
                "X-Request-ID": "request-one",
            },
        )
        original.set_cookie("session", "one", httponly=True, samesite="Strict")

        def handler(request):
            return original

        middleware = SirenDjangoMiddleware(
            get_response=handler,
            adapter=adapter,
            policy=CapabilityPolicy(),
        )
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            response = middleware(
                RequestFactory().get(
                    "/api/example_resources/one",
                    HTTP_ACCEPT="application/vnd.siren+json",
                    HTTP_IF_NONE_MATCH='"json"',
                )
            )

        for name in (
            "Accept-Ranges",
            "Content-Digest",
            "Content-Encoding",
            "Content-Range",
            "Digest",
            "ETag",
            "Last-Modified",
        ):
            assert name not in response
        assert response["Content-Type"] == "application/vnd.siren+json"
        assert "Content-Length" not in response
        assert response["Vary"] == "Origin, Cookie, Accept"
        assert response["Cache-Control"] == "private"
        assert response["Content-Security-Policy"] == "default-src 'none'"
        assert response["Location"] == "/api/example_resources/one"
        assert response["RateLimit-Limit"] == "100"
        assert response["WWW-Authenticate"] == 'Bearer realm="api"'
        assert response["X-Request-ID"] == "request-one"
        assert response.cookies["session"].value == "one"
        assert response.cookies["session"]["httponly"] is True
        assert response.cookies["session"]["samesite"] == "Strict"

    def test_django_bridge_passes_ineligible_responses_through_without_decoding(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/api")
        policy = CapabilityPolicy()
        factory = RequestFactory()
        cases = (
            ("/openapi.json", JsonResponse({"openapi": "3.1.1"})),
            ("/health", JsonResponse({"status": "ok"})),
            ("/missing", HttpResponse("<h1>Missing</h1>", status=404, content_type="text/html")),
            ("/api/example_resources/one", HttpResponse("<h1>ExampleResource</h1>", content_type="text/html")),
            ("/api/example_resources/one", HttpResponseRedirect("/login")),
            ("/api/example_resources/one", HttpResponse(status=304)),
            (
                "/api/example_resources/one",
                StreamingHttpResponse(iter((b'{"example_resource_key":"one"}',)), content_type="application/json"),
            ),
            ("/api/example_resources/one", FileResponse(BytesIO(b"example_resource"))),
            (
                "/api/example_resources/one",
                HttpResponse('{"class":["example_resource"]}', content_type="application/vnd.siren+json"),
            ),
        )
        calls = []
        responses = [response for _, response in cases]

        def handler(request):
            calls.append(request.path)
            return responses.pop(0)

        with override_settings(ALLOWED_HOSTS=["testserver"]):
            for path, response in cases:
                middleware = SirenDjangoMiddleware(
                    get_response=handler,
                    adapter=adapter,
                    policy=policy,
                )
                returned = middleware(
                    factory.get(
                        path,
                        HTTP_ACCEPT="application/vnd.siren+json",
                    )
                )

                assert returned is response
                if response.status_code == 304:
                    assert returned["Vary"] == "Accept"
                response.close()

        assert calls == [path for path, _ in cases]
        assert policy.calls == []

    def test_django_bridge_projects_matched_json_suffix_responses(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/api")
        policy = CapabilityPolicy()
        calls = []
        problem = HttpResponse(
            '{"detail":"Missing"}',
            status=404,
            content_type="application/problem+json; charset=utf-8",
        )

        def handler(request):
            calls.append(request.path)
            return problem

        middleware = SirenDjangoMiddleware(get_response=handler, adapter=adapter, policy=policy)
        factory = RequestFactory()
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            response = middleware(
                factory.delete(
                    "/api/example_resources/missing",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )

        assert response["Content-Type"] == "application/vnd.siren+json"
        assert json.loads(response.content)["properties"] == {"detail": "Missing", "status": 404}
        assert calls == ["/api/example_resources/missing"]
        assert policy.calls == [("delete_example_resource", 404)]

    def test_django_bridge_projects_browser_discovery_from_the_api_root(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/api")
        calls = []

        def handler(request):
            calls.append(request.path)
            return JsonResponse({"status": "ready"})

        middleware = SirenDjangoMiddleware(
            get_response=handler,
            adapter=adapter,
            policy=RootCapabilityPolicy(),
        )
        factory = RequestFactory()
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            response = middleware(
                factory.get(
                    "/api?view=full",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )

        payload = json.loads(response.content)
        assert payload["class"] == ["api", "entry-point"]
        assert payload["properties"] == {"status": "ready", "version": "4.0.0"}
        assert payload["links"][0]["href"] == "http://testserver/api?view=full"
        assert payload["links"][1]["href"] == "http://testserver/api/example_resources"
        assert calls == ["/api"]

    def test_django_bridge_dispatches_an_independent_public_mount_once(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")
        policy = CapabilityPolicy()
        calls = []

        def handler(request):
            calls.append(request.path)
            return JsonResponse({"example_resource_key": "one", "title": "One"})

        middleware = SirenDjangoMiddleware(get_response=handler, adapter=adapter, policy=policy)
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            response = middleware(
                RequestFactory().get(
                    "/siren/example_resources/one",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )

        assert calls == ["/api/example_resources/one"]
        assert json.loads(response.content)["links"][0]["href"] == ("http://testserver/siren/example_resources/one")

        ordinary = middleware(
            RequestFactory().get(
                "/siren/example_resources/one",
                HTTP_ACCEPT="application/json",
            )
        )

        assert json.loads(ordinary.content) == {"example_resource_key": "one", "title": "One"}
        assert calls == ["/api/example_resources/one", "/api/example_resources/one"]

    def test_django_bridge_restores_the_public_path_when_source_dispatch_fails(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")
        request = RequestFactory().get("/siren/example_resources/one")

        def handler(failed_request):
            assert failed_request.path == "/api/example_resources/one"
            raise RuntimeError("dispatch failed")

        middleware = SirenDjangoMiddleware(
            get_response=handler,
            adapter=adapter,
            policy=CapabilityPolicy(),
        )

        with pytest.raises(RuntimeError, match="dispatch failed"):
            middleware(request)

        assert request.path == "/siren/example_resources/one"
        assert request.path_info == "/siren/example_resources/one"

    def test_standard_django_loader_builds_one_fresh_adapter_without_application_middleware(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        django_openapi_provider.calls = 0
        configuration = {
            "OPENAPI": ("tests.framework_fixtures.django_openapi_provider.django_openapi_provider"),
            "SOURCE_PATH": "/api",
            "PUBLIC_PATH": "/siren",
            "PROFILES": ["sirenity.SirenStructuredFormProfile"],
        }
        factory = RequestFactory()

        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY=configuration,
            ROOT_URLCONF="tests.framework_fixtures.django_urls",
        ):
            handler = BaseHandler()
            handler.load_middleware()
            ordinary = handler.get_response(
                factory.get(
                    "/api/example_resources/one",
                    HTTP_ACCEPT="application/json",
                )
            )
            siren = handler.get_response(
                factory.get(
                    "/siren/example_resources/one",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )

        assert ordinary["Content-Type"].startswith("application/json")
        siren_payload = json.loads(siren.content)
        assert siren_payload["class"] == ["example-resource"]
        assert [action["name"] for action in siren_payload["actions"]] == ["get_example_resource"]
        assert siren["Content-Type"] == "application/vnd.siren+json"
        assert django_openapi_provider.calls == 1

        with override_settings(SIRENITY=configuration):
            SirenMiddleware(lambda request: JsonResponse({"example_resource_id": "two", "title": "Fresh"}))

        assert django_openapi_provider.calls == 2

    def test_standard_django_loader_accepts_a_direct_django_ninja_api(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        configuration = {
            "OPENAPI": "tests.framework_fixtures.django_ninja_api.django_ninja_api",
            "SOURCE_PATH": "/api",
            "PUBLIC_PATH": "/siren",
        }

        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF="tests.framework_fixtures.django_ninja_urls",
            SIRENITY=configuration,
        ):
            middleware = SirenMiddleware(
                lambda request: JsonResponse(
                    [{"example_resource_id": "example-resource-one", "title": "Example resource"}],
                    safe=False,
                )
            )
            response = middleware(
                RequestFactory().get(
                    "/siren/example_resources",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )

        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.siren+json"
        payload = json.loads(response.content)
        assert payload["title"] == "ExampleResource"
        assert payload["links"][0]["title"] == "ExampleResource"
        assert payload["entities"][0]["properties"] == {
            "example_resource_id": "example-resource-one",
            "title": "Example resource",
        }

    def test_standard_django_loader_follows_the_projected_root_action_across_trailing_slash_mounts(self):
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        configuration = {
            "OPENAPI": ("tests.framework_fixtures.django_openapi_provider.django_openapi_provider"),
            "SOURCE_PATH": "/api",
            "PUBLIC_PATH": "/siren",
        }
        factory = RequestFactory()

        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY=configuration,
            ROOT_URLCONF="tests.framework_fixtures.django_urls",
        ):
            handler = BaseHandler()
            handler.load_middleware()
            entry = handler.get_response(
                factory.get(
                    "/siren/",
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )
            action = json.loads(entry.content)["actions"][0]
            followed = handler.get_response(
                factory.get(
                    action["href"],
                    HTTP_ACCEPT="application/vnd.siren+json",
                )
            )

        assert action == {
            "name": "get_api_root",
            "href": "http://testserver/siren",
            "method": "GET",
            "title": "Read API entry point",
        }
        assert followed.status_code == 200
        assert followed["Content-Type"] == "application/vnd.siren+json"
        assert json.loads(followed.content)["properties"] == {
            "status": "ready",
            "version": "4.0.0",
        }

    def test_standard_django_loader_rejects_incomplete_configuration_at_startup(self):
        with (
            override_settings(SIRENITY={}),
            pytest.raises(SirenityError, match=r"SIRENITY\.OPENAPI"),
        ):
            SirenMiddleware(lambda request: JsonResponse({}))

    def test_public_configuration_resolves_one_adapter_lifecycle_for_django(self):
        django_openapi_provider.calls = 0

        configuration = siren_configuration(
            openapi=("tests.framework_fixtures.django_openapi_provider.django_openapi_provider"),
            source_path="/api",
            public_path="/siren",
            policy="tests.framework_fixtures.capability_policy.CapabilityPolicy",
        )

        assert isinstance(configuration, SirenConfiguration)
        assert configuration.adapter() is configuration.adapter()
        assert django_openapi_provider.calls == 1
        middleware = configuration.django(lambda request: JsonResponse({}))
        assert middleware.adapter is configuration.adapter()
        assert isinstance(middleware.policy, CapabilityPolicy)

    def test_root_import_keeps_django_optional(self):
        script = (
            "import builtins\n"
            "original = builtins.__import__\n"
            "def guarded(name, *args, **kwargs):\n"
            "    level = kwargs.get('level', args[3] if len(args) > 3 else 0)\n"
            "    if level == 0 and (name == 'django' or name.startswith('django.')):\n"
            "        raise AssertionError('core imported Django')\n"
            "    return original(name, *args, **kwargs)\n"
            "builtins.__import__ = guarded\n"
            "import sirenity\n"
        )

        result = subprocess.run((sys.executable, "-c", script), capture_output=True, text=True)

        assert result.returncode == 0, result.stderr
