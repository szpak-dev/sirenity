from copy import deepcopy
from typing import ClassVar
from urllib.parse import parse_qsl, urlsplit

import pytest

from sirenity import SirenAdapterRequest, SirenityError, siren_adapter


class TestPagination:
    schema: ClassVar[dict[str, object]] = {
        "openapi": "3.1.1",
        "info": {"title": "Pagination API", "version": "1.0.0"},
        "paths": {
            "/api/articles": {
                "get": {
                    "operationId": "list_articles",
                    "summary": "List articles",
                    "description": "List one bounded page of articles.",
                    "parameters": [
                        {
                            "name": "kind",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "title": "Kind"},
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "title": "Offset", "default": 0},
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "title": "Limit", "default": 2},
                        },
                        {
                            "name": "revision",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "title": "Revision"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Article page.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ArticlePage"}
                                }
                            },
                            "links": {
                                "next": {
                                    "operationId": "list_articles",
                                    "parameters": {
                                        "offset": "$response.body#/next_offset",
                                        "limit": "$response.body#/limit",
                                        "revision": "$response.body#/revision",
                                    },
                                }
                            },
                        }
                    },
                }
            },
            "/api/articles/{article_id}": {
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
                    "description": "Read one article.",
                    "responses": {
                        "200": {
                            "description": "Article.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Article"}
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
                    "required": ["id", "title"],
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                    },
                },
                "ArticlePage": {
                    "type": "object",
                    "title": "Article page",
                    "required": ["items", "has_more", "next_offset", "limit", "revision"],
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Article"},
                        },
                        "has_more": {"type": "boolean"},
                        "next_offset": {"type": "integer"},
                        "limit": {"type": "integer"},
                        "revision": {"type": "string"},
                        "facets": {"type": "array", "items": {"type": "string"}},
                    },
                },
            }
        },
    }

    def test_public_boundary_exposes_an_invokable_next_link_for_an_incomplete_page(self):
        assert "x-sirenity" not in str(self.schema["paths"])
        response = siren_adapter(self.schema, source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                operation_id="list_articles",
                status=200,
                result={
                    "items": [{"id": "article-1", "title": "First"}],
                    "has_more": True,
                    "next_offset": 2,
                    "limit": 2,
                    "revision": "opaque/revision-7",
                    "facets": ["featured"],
                },
                base_url="https://example.test",
                query=(("kind", "news"), ("offset", 0), ("limit", 2)),
            )
        )

        assert response.payload["class"] == ["collection", "article"]
        assert response.payload["properties"] == {
            "has_more": True,
            "next_offset": 2,
            "limit": 2,
            "revision": "opaque/revision-7",
            "facets": ["featured"],
        }
        assert response.payload["links"][-1] == {
            "rel": ["next"],
            "title": "Next page",
            "href": (
                "https://example.test/siren/articles?kind=news&offset=2&limit=2&"
                "revision=opaque%2Frevision-7"
            ),
        }

    def test_public_boundary_exposes_no_next_link_for_a_complete_page(self):
        response = siren_adapter(self.schema, source_path="/api", public_path="/siren").respond(
            SirenAdapterRequest(
                operation_id="list_articles",
                status=200,
                result={
                    "items": [{"id": "article-3", "title": "Last"}],
                    "has_more": False,
                    "next_offset": 4,
                    "limit": 2,
                    "revision": "opaque/revision-7",
                    "facets": ["featured"],
                },
                base_url="https://example.test",
                query=(("kind", "news"), ("offset", 2), ("limit", 2)),
            )
        )

        assert [link["rel"] for link in response.payload["links"]] == [["self"]]

    def test_browser_can_follow_the_visible_continuation_to_the_next_page(self):
        adapter = siren_adapter(self.schema, source_path="/api", public_path="/siren")
        first = adapter.respond(
            SirenAdapterRequest(
                operation_id="list_articles",
                status=200,
                result={
                    "items": [{"id": "article-1", "title": "First"}],
                    "has_more": True,
                    "next_offset": 2,
                    "limit": 2,
                    "revision": "opaque/revision-7",
                    "facets": ["featured"],
                },
                base_url="https://example.test",
                query=(("kind", "news"), ("offset", 0), ("limit", 2)),
            )
        )
        continuation = urlsplit(first.payload["links"][-1]["href"])

        match = adapter.match("GET", continuation.path)
        assert match is not None
        assert match.operation_id == "list_articles"
        second = adapter.respond(
            SirenAdapterRequest(
                operation_id=match.operation_id,
                status=200,
                result={
                    "items": [{"id": "article-3", "title": "Last"}],
                    "has_more": False,
                    "next_offset": 4,
                    "limit": 2,
                    "revision": "opaque/revision-7",
                    "facets": ["featured"],
                },
                base_url="https://example.test",
                query=tuple(parse_qsl(continuation.query)),
            )
        )

        assert second.payload["entities"][0]["properties"]["id"] == "article-3"
        assert [link["rel"] for link in second.payload["links"]] == [["self"]]

    def test_contract_rejects_pagination_without_required_has_more(self):
        schema = deepcopy(self.schema)
        schema["components"]["schemas"]["ArticlePage"]["required"].remove("has_more")

        with pytest.raises(SirenityError, match="has_more property must be required"):
            siren_adapter(schema, source_path="/api", public_path="/siren")

    def test_contract_rejects_nullable_has_more(self):
        schema = deepcopy(self.schema)
        schema["components"]["schemas"]["ArticlePage"]["properties"]["has_more"] = {
            "anyOf": [{"type": "boolean"}, {"type": "null"}]
        }

        with pytest.raises(SirenityError, match="non-nullable boolean has_more"):
            siren_adapter(schema, source_path="/api", public_path="/siren")

    def test_contract_rejects_an_ambiguous_page_item_collection(self):
        schema = deepcopy(self.schema)
        page = schema["components"]["schemas"]["ArticlePage"]
        page["properties"]["duplicates"] = {
            "type": "array",
            "items": {"$ref": "#/components/schemas/Article"},
        }
        page["required"].append("duplicates")

        with pytest.raises(SirenityError, match="exactly one array-of-object property"):
            siren_adapter(schema, source_path="/api", public_path="/siren")

    def test_contract_rejects_an_optional_continuation_value(self):
        schema = deepcopy(self.schema)
        schema["components"]["schemas"]["ArticlePage"]["required"].remove("next_offset")

        with pytest.raises(SirenityError, match="continuation properties must exist and be required"):
            siren_adapter(schema, source_path="/api", public_path="/siren")

    def test_contract_rejects_a_nullable_continuation_value(self):
        schema = deepcopy(self.schema)
        schema["components"]["schemas"]["ArticlePage"]["properties"]["next_offset"] = {
            "anyOf": [{"type": "integer"}, {"type": "null"}]
        }

        with pytest.raises(SirenityError, match="continuation properties must be non-nullable scalars"):
            siren_adapter(schema, source_path="/api", public_path="/siren")

    def test_contract_rejects_a_next_link_to_a_different_operation(self):
        schema = deepcopy(self.schema)
        schema["paths"]["/api/articles"]["get"]["responses"]["200"]["links"]["next"][
            "operationId"
        ] = "get_article"

        with pytest.raises(SirenityError, match="same collection GET operation"):
            siren_adapter(schema, source_path="/api", public_path="/siren")
