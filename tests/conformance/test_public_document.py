import pytest
from pytest_bdd import given, scenario, then, when

from sirenity.api import SirenDocument, SirenityError, SirenLink

from ..cases import SirenityCase


class PublicDocumentSteps:
    def invalid_relation(self) -> None:
        assert " " in "invalid relation"
    
    
    def create_link(self) -> None:
        with pytest.raises(SirenityError):
            SirenLink(rel=("invalid relation",), href="https://api.example.test/example-resources/1")
    
    
    def relation_is_rejected(self) -> None:
        with pytest.raises(SirenityError) as captured:
            SirenLink(rel=("invalid relation",), href="https://api.example.test/example-resources/1")
        assert str(captured.value) == "Siren URI must be a valid URI."
    
    
    def document(self) -> None:
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
    
    
    def serialize(self) -> None:
        payload = SirenDocument(class_=("example-resource",)).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )
        assert payload == {"class": ["example-resource"]}
    
    
    def official_members(self) -> None:
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
    
    
public_document_steps = PublicDocumentSteps()
invalid_relation = given("an invalid public Siren relation")(public_document_steps.invalid_relation)
create_link = when("the caller creates its link")(public_document_steps.create_link)
relation_is_rejected = then("the public boundary rejects the relation")(public_document_steps.relation_is_rejected)
document = given("an official public Siren document")(public_document_steps.document)
serialize = when("the caller serializes the document")(public_document_steps.serialize)
official_members = then("the payload contains only official members")(public_document_steps.official_members)


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
