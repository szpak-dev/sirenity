from sirenity.api import siren

from ..cases import OpenApiCase


class TestOpenApiRoutes(OpenApiCase):
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
