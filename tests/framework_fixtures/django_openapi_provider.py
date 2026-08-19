from dataclasses import dataclass


@dataclass
class DjangoOpenApiProvider:
    calls: int = 0

    def __call__(self):
        self.calls += 1
        return {
            "openapi": "3.1.1",
            "info": {"title": "Installed API", "version": "4.0.0"},
            "paths": {
                "/api/": {
                    "get": {
                        "operationId": "get_api_root",
                        "summary": "Read API entry point",
                        "description": "Read the API entry point.",
                        "responses": {
                            "200": {
                                "description": "API root",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "title": "API entry point",
                                            "properties": {"status": {"type": "string"}},
                                        }
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
                                "description": "Article",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "title": "Article",
                                            "properties": {
                                                "article_id": {"type": "string"},
                                                "title": {"type": "string"},
                                            },
                                            "required": ["article_id", "title"],
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }


django_openapi_provider = DjangoOpenApiProvider()
