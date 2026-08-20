type OpenApiDocument = dict[str, object]

calls: int = 0


def openapi_schema() -> OpenApiDocument:
    global calls
    calls += 1
    return {
        "openapi": "3.1.1",
        "info": {"title": "Example API", "version": "1"},
        "paths": {
            "/api/example_resources/{example_resource_id}": {
                "parameters": [
                    {
                        "name": "example_resource_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "patch": {
                    "operationId": "update_example_resource",
                    "summary": "Update example resource",
                    "description": "Update one example resource.",
                    "parameters": [
                        {
                            "name": "example_page",
                            "in": "query",
                            "schema": {"type": "integer", "title": "Example page"},
                        },
                        {
                            "name": "example_trace",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "example_session",
                            "in": "cookie",
                            "schema": {"type": "string"},
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "metadata"],
                                    "properties": {
                                        "title": {"type": "string", "title": "Title"},
                                        "metadata": {
                                            "type": "object",
                                            "properties": {"source": {"type": "string"}},
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Updated example resource.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "title": "Example resource",
                                        "properties": {
                                            "example_resource_id": {"type": "string"},
                                            "title": {"type": "string"},
                                            "metadata": {"type": "object"},
                                            "example_page": {"type": "integer"},
                                            "example_trace": {"type": "string"},
                                            "example_session": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
            }
        },
    }
