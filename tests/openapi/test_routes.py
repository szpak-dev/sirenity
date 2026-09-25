from sirenity.api import SirenScope, siren

from ..cases import OpenApiCase


class TestOpenApiRoutes(OpenApiCase):
    def test_nested_paginated_collection_owns_its_route_and_operations(self) -> None:
        engine = siren(
            self.contracts.nested_item_follow_ups(),
            source_path="/api",
            public_path="/siren",
        )

        resource = next(
            resource
            for resource in engine.api.resources
            if resource.collection.path == "/siren/example_records/{example_record_id}/example_items"
        )
        collection = next(operation for operation in engine.api.operations if operation.name == "list_example_items")
        entity = next(operation for operation in engine.api.operations if operation.name == "read_example_item_content")

        assert resource.entity.path == ""
        assert resource.collection_operations == ("list_example_items",)
        assert resource.entity_operations == ()
        assert collection.scope == SirenScope.COLLECTION
        assert entity.scope == SirenScope.ENTITY

    def test_collection_only_paginated_resource_uses_its_item_title(self) -> None:
        contract = self.contracts.pagination()
        del contract["paths"]["/api/example_records/{example_record_id}"]

        engine = siren(contract, source_path="/api", public_path="/siren")

        assert len(engine.api.resources) == 1
        resource = engine.api.resources[0]
        assert resource.collection.path == "/siren/example_records"
        assert resource.entity.path == ""
        assert resource.title == "Example record"
        assert resource.collection_operations == ("list_example_records",)

    def test_collection_only_array_resource_uses_its_item_title(self) -> None:
        contract = self.contracts.pagination()
        del contract["paths"]["/api/example_records/{example_record_id}"]
        operation = contract["paths"]["/api/example_records"]["get"]
        response = operation["responses"]["200"]
        response["content"]["application/json"]["schema"] = {
            "type": "array",
            "items": {"$ref": "#/components/schemas/ExampleRecord"},
        }
        del response["links"]

        engine = siren(contract, source_path="/api", public_path="/siren")

        resource = engine.api.resources[0]
        assert resource.entity.path == ""
        assert resource.title == "Example record"
        assert resource.collection_operations == ("list_example_records",)

    def test_collection_only_command_resource_uses_its_route_name(self) -> None:
        engine = siren(self.contracts.collection_command(), source_path="/api", public_path="/siren")

        resource = engine.api.resources[0]
        assert resource.collection.path == "/siren/example_records"
        assert resource.entity.path == ""
        assert resource.title == "Example record"
        assert resource.collection_operations == ("create_example_record",)
