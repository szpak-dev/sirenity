SCHEMA = {
    "openapi": "3.1.1",
    "info": {"title": "Sirenity", "version": "2"},
    "paths": {
        "/records": {
            "get": {
                "operationId": "list_records",
                "summary": "List records",
                "description": "List all records.",
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/records/{record_id}": {
            "parameters": [{"name": "record_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "get": {
                "operationId": "get_record",
                "summary": "Read record",
                "description": "Read one record.",
                "responses": {"200": {"description": "OK"}},
            },
            "patch": {
                "operationId": "rename_record",
                "summary": "Rename record",
                "description": "Rename one record.",
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
        "/records": {
            "get": {
                "operationId": "list_records",
                "summary": "List records",
                "description": "List all records.",
                "parameters": [{"$ref": "#/components/parameters/PageSize"}],
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/records/{record_id}": {
            "parameters": [{"name": "record_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "patch": {
                "operationId": "rename_record",
                "summary": "Rename record",
                "description": "Rename one record.",
                "requestBody": {"$ref": "#/components/requestBodies/RenameRecord"},
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
            "RenameRecord": {
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RenameRecord"}}},
            }
        },
        "schemas": {
            "PageSize": {"type": "integer", "title": "Page size"},
            "RenameRecord": {
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
        "/api/v2/teams/{team}/records": {
            "parameters": [
                {"name": "team", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "get": {
                "operationId": "list_team_records",
                "summary": "List team records",
                "description": "List records for one team.",
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/api/v2/teams/{team}/records/search": {
            "parameters": [
                {"name": "team", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "get": {
                "operationId": "search_team_records",
                "summary": "Search team records",
                "description": "Search records for one team.",
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/api/v2/teams/{team}/records/{record}": {
            "parameters": [
                {"name": "team", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "record", "in": "path", "required": True, "schema": {"type": "string"}},
            ],
            "get": {
                "operationId": "get_team_record",
                "summary": "Read team record",
                "description": "Read one team record.",
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/api/v2/teams/{team}/records/{record}/archive": {
            "parameters": [
                {"name": "team", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "record", "in": "path", "required": True, "schema": {"type": "string"}},
            ],
            "post": {
                "operationId": "archive_team_record",
                "summary": "Archive team record",
                "description": "Archive one team record.",
                "responses": {"204": {"description": "Archived"}},
            },
        },
        "/api/v2/teams/{team}/records/{record}/reports": {
            "parameters": [
                {"name": "team", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "record", "in": "path", "required": True, "schema": {"type": "string"}},
            ],
            "get": {
                "operationId": "list_record_reports",
                "summary": "List record reports",
                "description": "List reports for one record.",
                "responses": {"200": {"description": "OK"}},
            },
        },
    },
}

PARAMETER_MEDIA_SCHEMA = {
    "openapi": "3.1.1",
    "info": {"title": "Fields", "version": "1"},
    "paths": {
        "/records": {
            "parameters": [
                {"name": "page", "in": "query", "required": False, "schema": {"type": "integer", "title": "Page"}},
            ],
            "get": {
                "operationId": "list_records",
                "summary": "List records",
                "description": "List all records.",
                "parameters": [
                    {"name": "page", "in": "query", "required": False, "schema": {"type": "string", "title": "Page"}},
                ],
                "responses": {"200": {"description": "OK"}},
            },
        },
        "/records/{record_id}": {
            "parameters": [{"name": "record_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            "patch": {
                "operationId": "replace_record",
                "summary": "Replace record",
                "description": "Replace one record.",
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
