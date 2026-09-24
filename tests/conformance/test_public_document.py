import pytest
from pytest_bdd import given, scenario, then, when

from sirenity.api import SirenDocument, SirenityError, SirenLink

from ..cases import SirenityCase


class PublicDocumentSteps:
    @staticmethod
    @given("an invalid public Siren relation")
    def invalid_relation() -> None:
        assert " " in "invalid relation"
    
    
    @staticmethod
    @when("the caller creates its link")
    def create_link() -> None:
        with pytest.raises(SirenityError):
            SirenLink(rel=("invalid relation",), href="https://api.example.test/example-resources/1")
    
    
    @staticmethod
    @then("the public boundary rejects the relation")
    def relation_is_rejected() -> None:
        with pytest.raises(SirenityError) as captured:
            SirenLink(rel=("invalid relation",), href="https://api.example.test/example-resources/1")
        assert str(captured.value) == "Siren URI must be a valid URI."
    
    
    @staticmethod
    @given("an official public Siren document")
    def document() -> None:
        document = SirenDocument(
            class_=("example-resource",),
            properties={"example_resource_id": "example-resource-1"},
            links=(
                SirenLink(
                    rel=("self",),
                    href="https://api.example.test/example-resources/example-resource-1",
                ),
            ),
        )
        assert document.class_ == ("example-resource",)
    
    
    @staticmethod
    @when("the caller serializes the document")
    def serialize() -> None:
        payload = SirenDocument(class_=("example-resource",)).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        assert payload == {"class": ["example-resource"]}
    
    
    @staticmethod
    @then("the payload contains only official members")
    def official_members() -> None:
        payload = SirenDocument(
            class_=("example-resource",),
            properties={"example_resource_id": "example-resource-1"},
            links=(
                SirenLink(
                    rel=("self",),
                    href="https://api.example.test/example-resources/example-resource-1",
                ),
            ),
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
        assert payload == {
            "class": ["example-resource"],
            "properties": {"example_resource_id": "example-resource-1"},
            "links": [
                {
                    "rel": ["self"],
                    "href": "https://api.example.test/example-resources/example-resource-1",
                }
            ],
        }
    
    
class TestPublicDocumentAttacks(SirenityCase):
    @staticmethod
    @scenario("features/public_document.feature", "Invalid relation is rejected")
    def test_invalid_relation_is_rejected() -> None:
        pass

class TestPublicDocumentHappyPaths(SirenityCase):
    @staticmethod
    @scenario("features/public_document.feature", "Official document serializes through the public API")
    def test_official_document_serializes_through_the_public_api() -> None:
        pass
