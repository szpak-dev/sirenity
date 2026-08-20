from collections.abc import Mapping

from pytest_bdd import given, scenarios, then, when

from sirenity import SirenAction, SirenDocument, SirenEmbeddedLink, SirenLink


class EntitySteps:
    document: SirenDocument | None = None
    payload: Mapping[str, object] | None = None

    @staticmethod
    @given("a public root entity with official members", stacklevel=2)
    def public_root_entity_with_official_members() -> None:
        EntitySteps.payload = None
        EntitySteps.document = SirenDocument(
            class_=("example_resource",),
            title="Architecture",
            properties={"id": "42"},
            entities=(SirenEmbeddedLink(rel=("item",), href="https://api.example.com/example_resources/43"),),
            actions=(SirenAction(name="update", href="https://api.example.com/example_resources/42"),),
            links=(SirenLink(rel=("self",), href="https://api.example.com/example_resources/42"),),
        )

    @staticmethod
    @given("a public root entity with a self link", stacklevel=2)
    def public_root_entity_with_a_self_link() -> None:
        EntitySteps.payload = None
        EntitySteps.document = SirenDocument(
            links=(SirenLink(rel=("self",), href="https://api.example.com/example_resources/42"),),
        )

    @staticmethod
    @when("it is serialized", stacklevel=2)
    def serialized_root_entity() -> None:
        assert isinstance(EntitySteps.document, SirenDocument)
        EntitySteps.payload = EntitySteps.document.model_dump(by_alias=True, mode="json", exclude_none=True)

    @staticmethod
    @then("it has its class, title, and properties", stacklevel=2)
    def root_entity_has_its_state_members() -> None:
        assert EntitySteps.payload == {
            "class": ["example_resource"],
            "title": "Architecture",
            "properties": {"id": "42"},
            "entities": [{"rel": ["item"], "href": "https://api.example.com/example_resources/43"}],
            "actions": [{"name": "update", "method": "GET", "href": "https://api.example.com/example_resources/42"}],
            "links": [{"rel": ["self"], "href": "https://api.example.com/example_resources/42"}],
        }

    @staticmethod
    @then("it has its sub-entities, actions, and links", stacklevel=2)
    def root_entity_has_its_related_members() -> None:
        assert isinstance(EntitySteps.payload, Mapping)
        assert set(EntitySteps.payload) == {"class", "title", "properties", "entities", "actions", "links"}

    @staticmethod
    @then("it has a self link to its URI", stacklevel=2)
    def root_entity_has_a_self_link_to_its_uri() -> None:
        assert EntitySteps.payload == {
            "links": [{"rel": ["self"], "href": "https://api.example.com/example_resources/42"}]
        }


scenarios("../features/entity.feature")
