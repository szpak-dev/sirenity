from sirenity.api import siren

from ..cases import OpenApiCase


class TestOpenApiRoutes(OpenApiCase):
    def test_collection_only_resource_is_accepted(self) -> None:
        contract = self.contracts.pagination()
        del contract["paths"]["/api/example_records/{example_record_id}"]

        engine = siren(contract, source_path="/api", public_path="/siren")

        assert len(engine.api.resources) == 1
        resource = engine.api.resources[0]
        assert resource.collection.path == "/siren/example_records"
        assert resource.entity.path == ""
        assert resource.collection_operations == ("list_example_records",)
