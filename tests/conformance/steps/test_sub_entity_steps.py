from collections.abc import Mapping

from pytest_bdd import given, scenarios, then, when

from sirenity import SirenEmbeddedLink, SirenEmbeddedRepresentation, SirenityError


class SubEntitySteps:
    value: SirenEmbeddedLink | SirenEmbeddedRepresentation | None = None
    payload: Mapping[str, object] | None = None
    error: SirenityError | ValueError | None = None
    missing_value_type: type[SirenEmbeddedLink] | type[SirenEmbeddedRepresentation] | None = None
    invalid_media_type: str | None = None

    @staticmethod
    @given('a public embedded link with rel "item" and an href', stacklevel=2)
    def public_embedded_link_with_relation_and_href() -> None:
        SubEntitySteps.payload = None
        SubEntitySteps.error = None
        SubEntitySteps.missing_value_type = None
        SubEntitySteps.invalid_media_type = None
        SubEntitySteps.value = SirenEmbeddedLink(
            rel=("item",),
            href="https://api.example.com/example_resources/42",
            type="application/json",
        )

    @staticmethod
    @given("a public embedded link without an href", stacklevel=2)
    def public_embedded_link_without_an_href() -> None:
        SubEntitySteps.value = None
        SubEntitySteps.payload = None
        SubEntitySteps.error = None
        SubEntitySteps.missing_value_type = SirenEmbeddedLink
        SubEntitySteps.invalid_media_type = None

    @staticmethod
    @given("a public embedded link with an invalid media type", stacklevel=2)
    def public_embedded_link_with_an_invalid_media_type() -> None:
        SubEntitySteps.value = None
        SubEntitySteps.payload = None
        SubEntitySteps.error = None
        SubEntitySteps.missing_value_type = None
        SubEntitySteps.invalid_media_type = "not a media type"

    @staticmethod
    @given('a public embedded representation with rel "item"', stacklevel=2)
    def public_embedded_representation_with_relation() -> None:
        SubEntitySteps.payload = None
        SubEntitySteps.error = None
        SubEntitySteps.missing_value_type = None
        SubEntitySteps.invalid_media_type = None
        SubEntitySteps.value = SirenEmbeddedRepresentation(rel=("item",), properties={"id": "42"})

    @staticmethod
    @given("a public embedded representation without rel", stacklevel=2)
    def public_embedded_representation_without_relation() -> None:
        SubEntitySteps.value = None
        SubEntitySteps.payload = None
        SubEntitySteps.error = None
        SubEntitySteps.missing_value_type = SirenEmbeddedRepresentation
        SubEntitySteps.invalid_media_type = None

    @staticmethod
    @when("it is created", stacklevel=2)
    def created_sub_entity() -> None:
        try:
            if SubEntitySteps.invalid_media_type is not None:
                SubEntitySteps.value = SirenEmbeddedLink(
                    rel=("item",),
                    href="https://api.example.com/example_resources/42",
                    type=SubEntitySteps.invalid_media_type,
                )
            if SubEntitySteps.missing_value_type is SirenEmbeddedLink:
                SubEntitySteps.value = SirenEmbeddedLink(rel=("item",))
            if SubEntitySteps.missing_value_type is SirenEmbeddedRepresentation:
                SubEntitySteps.value = SirenEmbeddedRepresentation()
        except (SirenityError, ValueError) as error:
            SubEntitySteps.error = error

    @staticmethod
    @when("it is serialized", stacklevel=2)
    def serialized_sub_entity() -> None:
        assert isinstance(SubEntitySteps.value, SirenEmbeddedLink | SirenEmbeddedRepresentation)
        SubEntitySteps.payload = SubEntitySteps.value.model_dump(by_alias=True, mode="json", exclude_none=True)

    @staticmethod
    @then('the embedded link has rel "item" and its href', stacklevel=2)
    def embedded_link_has_relation_and_href() -> None:
        assert SubEntitySteps.payload == {
            "rel": ["item"],
            "href": "https://api.example.com/example_resources/42",
            "type": "application/json",
        }

    @staticmethod
    @then('the embedded representation has rel "item"', stacklevel=2)
    def embedded_representation_has_relation() -> None:
        assert SubEntitySteps.payload == {"properties": {"id": "42"}, "rel": ["item"]}

    @staticmethod
    @then("creation is rejected", stacklevel=2)
    def sub_entity_creation_is_rejected() -> None:
        if SubEntitySteps.invalid_media_type is not None:
            assert str(SubEntitySteps.error) == "Siren media type must use the official media-type grammar."
        elif SubEntitySteps.missing_value_type is SirenEmbeddedLink:
            assert isinstance(SubEntitySteps.error, ValueError)
            errors = SubEntitySteps.error.errors(include_url=False)
            assert errors[0]["loc"] == ("href",)
            assert errors[0]["type"] == "missing"
        else:
            assert isinstance(SubEntitySteps.error, ValueError)
            errors = SubEntitySteps.error.errors(include_url=False)
            assert errors[0]["loc"] == ("rel",)
            assert errors[0]["type"] == "missing"


scenarios("../features/sub_entities.feature")
