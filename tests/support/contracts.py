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

    def explicit_pagination(self) -> dict[str, object]:
        contract = self.pagination()
        operation = contract["paths"]["/api/example_records"]["get"]
        operation["parameters"][0]["required"] = True
        operation["parameters"].append(
            {
                "name": "example_noise",
                "in": "query",
                "schema": {"type": "string", "title": "Example noise"},
            }
        )
        operation["responses"]["200"]["links"]["next"]["x-sirenity"] = {
            "sourceInputs": {
                "query.example_filter": "$request.query.example_filter",
            }
        }
        return contract

    def item_follow_ups(self) -> dict[str, object]:
        return {
            "openapi": "3.1.1",
            "info": {"title": "Example items API", "version": "1.0.0"},
            "paths": {
                "/api/example_items": {
                    "get": {
                        "operationId": "list_example_items",
                        "summary": "List example items",
                        "description": "List one page of example item manifests.",
                        "parameters": [
                            {
                                "name": "offset",
                                "in": "query",
                                "schema": {"type": "integer", "title": "Offset", "default": 0},
                            },
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer", "title": "Limit", "default": 2},
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Example item page.",
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/ExampleItemPage"}}
                                },
                                "links": {
                                    "next": {
                                        "operationId": "list_example_items",
                                        "parameters": {
                                            "offset": "$response.body#/next_offset",
                                            "limit": "$response.body#/limit",
                                        },
                                    },
                                    "content": {
                                        "operationId": "read_example_item_content",
                                        "parameters": {
                                            "path.item_id": "$response.body#/item_id",
                                            "query.expected_revision": "$response.body#/expected_revision",
                                        },
                                        "x-sirenity": {
                                            "rel": "item",
                                            "scope": "entity",
                                            "itemCollection": "$response.body#/items",
                                        },
                                    },
                                },
                            }
                        },
                    }
                },
                "/api/example_items/{item_id}": {
                    "parameters": [
                        {
                            "name": "item_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "read_example_item_content",
                        "summary": "Read example item content",
                        "description": "Read one example item's content.",
                        "parameters": [
                            {
                                "name": "expected_revision",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string", "title": "Expected revision"},
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Example item content.",
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/ExampleItemContent"}}
                                },
                            }
                        },
                    },
                },
            },
            "components": {
                "schemas": {
                    "ExampleItemManifest": {
                        "type": "object",
                        "title": "Example item manifest",
                        "required": ["item_id", "expected_revision"],
                        "properties": {
                            "item_id": {"type": "string"},
                            "expected_revision": {"type": "string"},
                        },
                    },
                    "ExampleItemPage": {
                        "type": "object",
                        "title": "Example item page",
                        "required": ["items", "has_more", "next_offset", "limit"],
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/ExampleItemManifest"},
                            },
                            "has_more": {"type": "boolean"},
                            "next_offset": {"type": "integer"},
                            "limit": {"type": "integer"},
                        },
                    },
                    "ExampleItemContent": {
                        "type": "object",
                        "title": "Example item content",
                        "required": ["item_id", "expected_revision", "content"],
                        "properties": {
                            "item_id": {"type": "string"},
                            "expected_revision": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                }
            },
        }

    def nested_item_follow_ups(self) -> dict[str, object]:
        contract = self.item_follow_ups()
        collection = contract["paths"].pop("/api/example_items")
        collection["parameters"] = [
            {
                "name": "example_record_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
        operation = collection["get"]
        operation["parameters"].insert(
            0,
            {
                "name": "example_filter",
                "in": "query",
                "required": True,
                "schema": {"type": "string", "title": "Example filter"},
            },
        )
        links = operation["responses"]["200"]["links"]
        links["next"]["x-sirenity"] = {
            "sourceInputs": {
                "path.example_record_id": "$request.path.example_record_id",
                "query.example_filter": "$request.query.example_filter",
            }
        }
        links["content"]["x-sirenity"]["sourceInputs"] = {
            "path.example_record_id": "$request.path.example_record_id",
        }
        contract["paths"]["/api/example_records/{example_record_id}/example_items"] = collection

        item = contract["paths"].pop("/api/example_items/{item_id}")
        item["parameters"].insert(
            0,
            {
                "name": "example_record_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            },
        )
        contract["paths"]["/api/example_records/{example_record_id}/example_item_contents/{item_id}"] = item

        contract["paths"]["/api/example_records/{example_record_id}"] = {
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
                "parameters": [
                    {
                        "name": "example_filter",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "title": "Example filter"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Example record.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ExampleRecord"}}},
                        "links": {
                            "items": {
                                "operationId": "list_example_items",
                                "parameters": {
                                    "path.example_record_id": "$response.body#/example_record_id",
                                },
                                "x-sirenity": {
                                    "rel": "collection",
                                    "scope": "collection",
                                    "sourceInputs": {
                                        "query.example_filter": "$request.query.example_filter",
                                    },
                                },
                            }
                        },
                    }
                },
            },
        }
        contract["components"]["schemas"]["ExampleRecord"] = {
            "type": "object",
            "title": "Example record",
            "required": ["example_record_id", "example_title"],
            "properties": {
                "example_record_id": {"type": "string"},
                "example_title": {"type": "string"},
            },
        }
        return contract

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

    def collection_command(self) -> dict[str, object]:
        contract = self.creation_verification()
        del contract["paths"]["/api/example_records/{example_record_id}"]
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

    def follow_ups(self) -> dict[str, object]:
        return {
            "openapi": "3.1.1",
            "info": {"title": "Example follow-ups API", "version": "1.0.0"},
            "paths": {
                "/api/example_dashboards/{example_dashboard_id}": {
                    "parameters": [
                        {
                            "name": "example_dashboard_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "get_example_dashboard",
                        "summary": "Read example dashboard",
                        "description": "Read one example dashboard.",
                        "responses": {
                            "200": {
                                "description": "Example dashboard.",
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/components/schemas/ExampleDashboard"}}
                                },
                                "links": {
                                    "primary_record": {
                                        "operationId": "get_example_record",
                                        "parameters": {"path.example_record_id": "$response.body#/primary_record_id"},
                                        "x-sirenity": {"rel": "item", "scope": "entity"},
                                    },
                                    "secondary_record": {
                                        "operationId": "get_example_record",
                                        "parameters": {"path.example_record_id": "$response.body#/secondary_record_id"},
                                        "x-sirenity": {"rel": "alternate", "scope": "entity"},
                                    },
                                },
                            }
                        },
                    },
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
                        "parameters": [
                            {
                                "name": "example_locale",
                                "in": "query",
                                "schema": {
                                    "type": "string",
                                    "title": "Example locale",
                                    "default": "example-en",
                                },
                            }
                        ],
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
                    "ExampleDashboard": {
                        "type": "object",
                        "title": "Example dashboard",
                        "required": [
                            "example_dashboard_id",
                            "primary_record_id",
                            "secondary_record_id",
                        ],
                        "properties": {
                            "example_dashboard_id": {"type": "string"},
                            "primary_record_id": {"type": "string"},
                            "secondary_record_id": {"type": "string"},
                        },
                    },
                    "ExampleRecord": {
                        "type": "object",
                        "title": "Example record",
                        "required": ["example_record_id", "example_title"],
                        "properties": {
                            "example_record_id": {"type": "string"},
                            "example_title": {"type": "string"},
                        },
                    },
                }
            },
        }

    def single_follow_up(self) -> dict[str, object]:
        contract = self.follow_ups()
        links = contract["paths"]["/api/example_dashboards/{example_dashboard_id}"]["get"]["responses"]["200"]["links"]
        del links["secondary_record"]
        return contract

    def project_follow_ups(self) -> dict[str, object]:
        contract = self.follow_ups()
        path = contract["paths"]["/api/example_dashboards/{example_dashboard_id}"]
        summary = deepcopy(path["get"])
        summary["operationId"] = "get_example_dashboard_summary"
        summary["summary"] = "Read example dashboard summary"
        summary["description"] = "Read one example dashboard summary."
        path["get"]["responses"]["200"].pop("links")
        contract["paths"]["/api/example_dashboards/{example_dashboard_id}/summary"] = {
            "parameters": deepcopy(path["parameters"]),
            "get": summary,
        }
        return contract

    def unsupported_follow_up(self) -> dict[str, object]:
        contract = self.single_follow_up()
        target = contract["paths"]["/api/example_records/{example_record_id}"]["get"]
        target["parameters"].append(
            {
                "name": "example_authorization",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
            }
        )
        return contract

    def required_query_follow_up(self) -> dict[str, object]:
        contract = self.single_follow_up()
        target = contract["paths"]["/api/example_records/{example_record_id}"]["get"]
        target["parameters"][0]["required"] = True
        source = contract["paths"]["/api/example_dashboards/{example_dashboard_id}"]["get"]
        source["parameters"] = [
            {
                "name": "example_noise",
                "in": "query",
                "schema": {"type": "string", "title": "Example noise"},
            }
        ]
        source["responses"]["200"]["links"]["primary_record"]["x-sirenity"]["sourceInputs"] = {
            "query.example_locale": "$request.path.example_dashboard_id"
        }
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
