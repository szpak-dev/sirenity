from copy import deepcopy


class ExampleContracts:
    def bounded(self) -> dict[str, object]:
        return {
            "openapi": "3.1.1",
            "info": {"title": "Example jobs API", "version": "1.0.0"},
            "paths": {
                "/api/example_jobs/{example_job_id}": {
                    "parameters": [
                        {
                            "name": "example_job_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_example_job",
                        "summary": "Read example job",
                        "description": "Read the current state of one example job.",
                        "parameters": [
                            {
                                "name": "example_filter",
                                "in": "query",
                                "schema": {"type": "string", "title": "Example filter"},
                            },
                            {
                                "name": "example_cursor",
                                "in": "query",
                                "schema": {"type": "string", "title": "Example cursor"},
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Example job state.",
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/ExampleJobState"}}
                                },
                                "links": {
                                    "next": {
                                        "operationId": "get_example_job",
                                        "parameters": {"example_cursor": "$response.body#/next_example_cursor"},
                                        "x-sirenity": {"continuation": "bounded"},
                                    }
                                },
                            }
                        },
                    },
                }
            },
            "components": {
                "schemas": {
                    "ExampleJobState": {
                        "type": "object",
                        "title": "Example job state",
                        "required": [
                            "example_job_id",
                            "example_state",
                            "has_more",
                            "next_example_cursor",
                        ],
                        "properties": {
                            "example_job_id": {"type": "string"},
                            "example_state": {"type": "string"},
                            "has_more": {"type": "boolean"},
                            "next_example_cursor": {"type": "string"},
                            "example_notes": {"type": "array", "items": {"type": "string"}},
                        },
                    }
                }
            },
        }

    def pagination(self) -> dict[str, object]:
        return {
            "openapi": "3.1.1",
            "info": {"title": "Example records API", "version": "1.0.0"},
            "paths": {
                "/api/example_records": {
                    "get": {
                        "operationId": "list_example_records",
                        "summary": "List example records",
                        "description": "List one page of example records.",
                        "parameters": [
                            {
                                "name": "example_filter",
                                "in": "query",
                                "schema": {"type": "string", "title": "Example filter"},
                            },
                            {
                                "name": "example_offset",
                                "in": "query",
                                "schema": {
                                    "type": "integer",
                                    "title": "Example offset",
                                    "default": 0,
                                },
                            },
                            {
                                "name": "example_limit",
                                "in": "query",
                                "schema": {
                                    "type": "integer",
                                    "title": "Example limit",
                                    "default": 2,
                                },
                            },
                            {
                                "name": "example_revision",
                                "in": "query",
                                "schema": {"type": "string", "title": "Example revision"},
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Example record page.",
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/ExampleRecordPage"}}
                                },
                                "links": {
                                    "next": {
                                        "operationId": "list_example_records",
                                        "parameters": {
                                            "example_offset": "$response.body#/next_example_offset",
                                            "example_limit": "$response.body#/example_limit",
                                            "example_revision": "$response.body#/example_revision",
                                        },
                                    }
                                },
                            }
                        },
                    }
                },
                "/api/example_records/{example_record_id}": {
                    "parameters": [
                        {
                            "name": "example_record_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_example_record",
                        "summary": "Read example record",
                        "description": "Read one example record.",
                        "responses": {
                            "200": {
                                "description": "Example record.",
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/ExampleRecord"}}
                                },
                            }
                        },
                    },
                },
            },
            "components": {
                "schemas": {
                    "ExampleRecord": {
                        "type": "object",
                        "title": "Example record",
                        "required": ["example_record_id", "example_title"],
                        "properties": {
                            "example_record_id": {"type": "string"},
                            "example_title": {"type": "string"},
                        },
                    },
                    "ExampleRecordPage": {
                        "type": "object",
                        "title": "Example record page",
                        "required": [
                            "example_items",
                            "has_more",
                            "next_example_offset",
                            "example_limit",
                            "example_revision",
                        ],
                        "properties": {
                            "example_items": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/ExampleRecord"},
                            },
                            "has_more": {"type": "boolean"},
                            "next_example_offset": {"type": "integer"},
                            "example_limit": {"type": "integer"},
                            "example_revision": {"type": "string"},
                            "example_facets": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                }
            },
        }

    def entity(self) -> dict[str, object]:
        contract = self.bounded()
        response = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]["responses"]["200"]
        del response["links"]
        return contract

    def operation(self) -> dict[str, object]:
        return {
            "openapi": "3.1.1",
            "info": {"title": "Example operations API", "version": "1.0.0"},
            "paths": {
                "/api/example_records/{example_record_id}": {
                    "parameters": [
                        {
                            "name": "example_record_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "minLength": 1},
                        }
                    ],
                    "patch": {
                        "operationId": "update_example_record",
                        "summary": "Update example record",
                        "description": "Update one example record.",
                        "parameters": [
                            {
                                "name": "example_page",
                                "in": "query",
                                "schema": {"type": "integer", "title": "Example page", "minimum": 1},
                            },
                            {
                                "name": "example_trace",
                                "in": "header",
                                "required": True,
                                "schema": {"type": "string", "title": "Example trace"},
                            },
                            {
                                "name": "example_session",
                                "in": "cookie",
                                "schema": {"type": "string", "title": "Example session"},
                            },
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["example_title", "example_metadata"],
                                        "properties": {
                                            "example_title": {
                                                "type": "string",
                                                "title": "Example title",
                                            },
                                            "example_metadata": {
                                                "type": "object",
                                                "properties": {"example_source": {"type": "string"}},
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Updated example record.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "title": "Example record",
                                            "required": ["example_record_id", "example_title"],
                                            "properties": {
                                                "example_record_id": {"type": "string"},
                                                "example_title": {"type": "string"},
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

    def verification(self) -> dict[str, object]:
        contract = self.operation()
        path = contract["paths"]["/api/example_records/{example_record_id}"]
        path["patch"]["responses"]["200"]["links"] = {
            "verification": {
                "operationId": "get_example_record",
                "parameters": {
                    "path.example_record_id": "$response.body#/example_record_id",
                },
                "x-sirenity": {"rel": "self", "scope": "entity"},
            }
        }
        path["get"] = {
            "operationId": "get_example_record",
            "summary": "Read example record",
            "description": "Read one example record.",
            "responses": {
                "200": {
                    "description": "Example record.",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "title": "Example record",
                                "required": ["example_record_id", "example_title"],
                                "properties": {
                                    "example_record_id": {"type": "string"},
                                    "example_title": {"type": "string"},
                                },
                            }
                        }
                    },
                }
            },
        }
        return contract

    def creation_verification(self) -> dict[str, object]:
        contract = self.verification()
        entity = contract["paths"]["/api/example_records/{example_record_id}"]
        create = entity.pop("patch")
        del create["responses"]["200"]["links"]
        create["operationId"] = "create_example_record"
        create["summary"] = "Create example record"
        create["description"] = "Create one example record."
        contract["paths"]["/api/example_records"] = {"post": create}
        return contract

    def unsupported_verification(self) -> dict[str, object]:
        contract = self.verification()
        target = contract["paths"]["/api/example_records/{example_record_id}"]["get"]
        target["parameters"] = [
            {
                "name": "example_authorization",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
        return contract

    def cross_operation_bounded(self) -> dict[str, object]:
        contract = self.bounded()
        source = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]
        source["parameters"].append(
            {
                "name": "example_source_only",
                "in": "query",
                "schema": {"type": "string", "title": "Example source only"},
            }
        )
        state = contract["components"]["schemas"]["ExampleJobState"]
        state["required"].extend(["next_example_output_id", "next_example_locale"])
        state["properties"].update(
            {
                "next_example_output_id": {"type": "string"},
                "next_example_locale": {"type": "string"},
            }
        )
        source["responses"]["200"]["links"]["next"] = {
            "operationId": "get_example_job_output",
            "parameters": {
                "path.example_output_id": "$response.body#/next_example_output_id",
                "query.example_locale": "$response.body#/next_example_locale",
            },
            "x-sirenity": {"continuation": "bounded"},
        }
        contract["paths"]["/api/example_jobs/{example_job_id}/example_outputs/{example_output_id}"] = {
            "parameters": [
                {
                    "name": "example_job_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                },
                {
                    "name": "example_output_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                },
            ],
            "get": {
                "operationId": "get_example_job_output",
                "summary": "Read example job output",
                "description": "Read one output produced by an example job.",
                "parameters": [
                    {
                        "name": "example_filter",
                        "in": "query",
                        "schema": {"type": "string", "title": "Example filter"},
                    },
                    {
                        "name": "example_locale",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "title": "Example locale"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Example job output.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "title": "Example job output",
                                    "required": ["example_output_id"],
                                    "properties": {"example_output_id": {"type": "string"}},
                                }
                            }
                        },
                    }
                },
            },
        }
        return contract

    def copy(self, contract: dict[str, object]) -> dict[str, object]:
        return deepcopy(contract)
