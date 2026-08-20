SCHEMA = {
    "openapi": "3.1.1",
    "info": {"title": "Sirenity", "version": "2"},
    "paths": {
        "/example_resources": {
            "get": {
                "operationId": "list_example_resources",
                "summary": "List example resources",
                "description": "List all example resources.",
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/example_resources/{example_resource_id}": {
            "parameters": [
                {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "get": {
                "operationId": "get_example_resource",
                "summary": "Read example resource",
                "description": "Read one example resource.",
                "responses": {"200": {"description": "OK"}},
            },
            "patch": {
                "operationId": "rename_example_resource",
                "summary": "Rename example resource",
                "description": "Rename one example resource.",
                "responses": {"200": {"description": "OK"}},
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"title": {"type": "string", "title": "Title"}},
                            }
                        }
                    }
                },
            },
        },
    },
}

REFERENCED_SCHEMA = {
    "openapi": "3.1.1",
    "info": {"title": "Sirenity", "version": "2"},
    "paths": {
        "/example_resources": {
            "get": {
                "operationId": "list_example_resources",
                "summary": "List example resources",
                "description": "List all example resources.",
                "parameters": [{"$ref": "#/components/parameters/PageSize"}],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/example_resources/{example_resource_id}": {
            "parameters": [
                {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "patch": {
                "operationId": "rename_example_resource",
                "summary": "Rename example resource",
                "description": "Rename one example resource.",
                "requestBody": {"$ref": "#/components/requestBodies/RenameExampleResource"},
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
    "components": {
        "parameters": {
            "PageSize": {
                "name": "page_size",
                "in": "query",
                "required": False,
                "schema": {"$ref": "#/components/schemas/PageSize"},
            }
        },
        "requestBodies": {
            "RenameExampleResource": {
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RenameExampleResource"}}},
            }
        },
        "schemas": {
            "PageSize": {"type": "integer", "title": "Page size"},
            "RenameExampleResource": {
                "type": "object",
                "properties": {"title": {"$ref": "#/components/schemas/Title", "type": "string", "title": "Title"}},
            },
            "Title": {"type": "integer"},
        },
    },
}

ROUTE_POLICY_SCHEMA = {
    "openapi": "3.1.1",
    "info": {"title": "Routes", "version": "1"},
    "paths": {
        "/api/v2/labels": {
            "get": {
                "operationId": "list_labels",
                "summary": "List labels",
                "description": "List all labels.",
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "operationId": "create_label",
                "summary": "Create label",
                "description": "Create one label.",
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/api/v2/example_groups/{example_group}/example_resources": {
            "parameters": [{"name": "example_group", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "operationId": "list_example_group_example_resources",
                "summary": "List example group example resources",
                "description": "List example resources for one example group.",
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/api/v2/example_groups/{example_group}/example_resources/search": {
            "parameters": [{"name": "example_group", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "operationId": "search_example_group_example_resources",
                "summary": "Search example group example resources",
                "description": "Search example resources for one example group.",
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/api/v2/example_groups/{example_group}/example_resources/{example_resource}": {
            "parameters": [
                {"name": "example_group", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "example_resource", "in": "path", "required": True, "schema": {"type": "string"}},
            ],
            "get": {
                "operationId": "get_example_group_example_resource",
                "summary": "Read example group example resource",
                "description": "Read one example group example resource.",
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/api/v2/example_groups/{example_group}/example_resources/{example_resource}/archive": {
            "parameters": [
                {"name": "example_group", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "example_resource", "in": "path", "required": True, "schema": {"type": "string"}},
            ],
            "post": {
                "operationId": "archive_example_group_example_resource",
                "summary": "Archive example group example resource",
                "description": "Archive one example group example resource.",
                "responses": {"204": {"description": "Archived"}},
            },
        },
        "/api/v2/example_groups/{example_group}/example_resources/{example_resource}/reports": {
            "parameters": [
                {"name": "example_group", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "example_resource", "in": "path", "required": True, "schema": {"type": "string"}},
            ],
            "get": {
                "operationId": "list_example_resource_reports",
                "summary": "List example resource reports",
                "description": "List reports for one example resource.",
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
}

PARAMETER_MEDIA_SCHEMA = {
    "openapi": "3.1.1",
    "info": {"title": "Fields", "version": "1"},
    "paths": {
        "/example_resources": {
            "parameters": [
                {"name": "page", "in": "query", "required": False, "schema": {"type": "integer", "title": "Page"}},
            ],
            "get": {
                "operationId": "list_example_resources",
                "summary": "List example resources",
                "description": "List all example resources.",
                "parameters": [
                    {"name": "page", "in": "query", "required": False, "schema": {"type": "string", "title": "Page"}},
                ],
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/example_resources/{example_resource_id}": {
            "parameters": [
                {"name": "example_resource_id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "patch": {
                "operationId": "replace_example_resource",
                "summary": "Replace example resource",
                "description": "Replace one example resource.",
                "requestBody": {
                    "content": {
                        "text/plain": {"schema": {"type": "string"}},
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"title": {"type": "string", "title": "Title"}},
                            }
                        },
                    }
                },
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
}
