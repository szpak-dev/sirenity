from collections.abc import Mapping

from pytest_bdd import given, scenarios, then, when

from sirenity import SirenEmbeddedRepresentation, SirenityError, SirenLink


class RelationSteps:
    value: SirenEmbeddedRepresentation | SirenLink | None = None
    payload: Mapping[str, object] | None = None
    error: SirenityError | None = None
    invalid: bool = False

    @staticmethod
    @given("a public link with an invalid relation", stacklevel=2)
    def public_link_with_invalid_relation() -> None:
        RelationSteps.value = None
        RelationSteps.payload = None
        RelationSteps.error = None
        RelationSteps.invalid = True

    @staticmethod
    @given("a public link with a relation URI", stacklevel=2)
    def public_link_with_relation_uri() -> None:
        RelationSteps.payload = None
        RelationSteps.error = None
        RelationSteps.invalid = False
        RelationSteps.value = SirenLink(
            rel=("https://rels.example.com/approval",), href="https://api.example.com/42")

    @staticmethod
    @given("a public embedded representation with a relation URI", stacklevel=2)
    def public_embedded_representation_with_relation_uri() -> None:
        RelationSteps.payload = None
        RelationSteps.error = None
        RelationSteps.invalid = False
        RelationSteps.value = SirenEmbeddedRepresentation(
            rel=("https://rels.example.com/approval",),
            properties={"id": "42"},
        )

    @staticmethod
    @when("it is created", stacklevel=2)
    def created_relation() -> None:
        try:
            if RelationSteps.invalid:
                RelationSteps.value = SirenLink(
                    rel=("invalid relation",), href="https://api.example.com/42")
        except SirenityError as error:
            RelationSteps.error = error

    @staticmethod
    @when("it is serialized", stacklevel=2)
    def serialized_relation() -> None:
        assert isinstance(RelationSteps.value,
                          SirenEmbeddedRepresentation | SirenLink)
        RelationSteps.payload = RelationSteps.value.model_dump(
            by_alias=True, mode="json", exclude_none=True)

    @staticmethod
    @then("creation is rejected", stacklevel=2)
    def relation_creation_is_rejected() -> None:
        assert str(
            RelationSteps.error) == "Siren relation must be an official relation token or URI."

    @staticmethod
    @then("the link has its relation URI", stacklevel=2)
    def link_has_relation_uri() -> None:
        assert RelationSteps.payload == {
            "rel": ["https://rels.example.com/approval"],
            "href": "https://api.example.com/42",
        }

    @staticmethod
    @then("the embedded representation has its relation URI", stacklevel=2)
    def embedded_representation_has_relation_uri() -> None:
        assert RelationSteps.payload == {
            "properties": {"id": "42"},
            "rel": ["https://rels.example.com/approval"],
        }


scenarios("../features/relations.feature")
