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
                "/api/example_resources/{example_resource_id}": {
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
                        "description": "Read one example resource.",
                        "responses": {
                            "200": {
                                "description": "Example resource.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "title": "Example resource",
                                            "properties": {
                                                "example_resource_id": {"type": "string"},
                                                "title": {"type": "string"},
                                            },
                                            "required": ["example_resource_id", "title"],
                                        }
                                    }
                                },
                            }
                        },
                    },
                },
            },
        }


django_openapi_provider = DjangoOpenApiProvider()
