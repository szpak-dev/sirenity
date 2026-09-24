import pytest

from sirenity.api import SirenContractError, siren

from ..cases import OpenApiCase


class TestOpenApiItemFollowUpAttacks(OpenApiCase):
    def test_unknown_target_is_rejected(self) -> None:
        contract = self.contracts.item_follow_ups()
        self.item_link(contract)["operationId"] = "missing_operation"

        with pytest.raises(SirenContractError, match="references unknown operation"):
            siren(contract, source_path="/api", public_path="/siren")

    def test_unknown_target_argument_is_rejected(self) -> None:
        contract = self.contracts.item_follow_ups()
        self.item_link(contract)["parameters"]["path.missing_id"] = "$response.body#/item_id"

        with pytest.raises(SirenContractError, match="parameters do not match the target route"):
            siren(contract, source_path="/api", public_path="/siren")

    def test_missing_required_target_input_is_rejected(self) -> None:
        contract = self.contracts.item_follow_ups()
        del self.item_link(contract)["parameters"]["query.expected_revision"]

        with pytest.raises(SirenContractError, match="does not satisfy required target query inputs"):
            siren(contract, source_path="/api", public_path="/siren")

    def test_non_item_relative_expression_is_rejected(self) -> None:
        contract = self.contracts.item_follow_ups()
        self.item_link(contract)["parameters"]["path.item_id"] = "$response.body#/items/0/item_id"

        with pytest.raises(SirenContractError, match="item follow-up parameter expression is invalid"):
            siren(contract, source_path="/api", public_path="/siren")

    def test_optional_item_property_is_rejected(self) -> None:
        contract = self.contracts.item_follow_ups()
        contract["components"]["schemas"]["ExampleItemManifest"]["required"].remove("expected_revision")

        with pytest.raises(SirenContractError, match="properties must exist and be required"):
            siren(contract, source_path="/api", public_path="/siren")

    def item_link(self, contract: dict[str, object]) -> dict[str, object]:
        return contract["paths"]["/api/example_items"]["get"]["responses"]["200"]["links"]["content"]
