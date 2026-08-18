from collections.abc import Mapping

from pydantic import Field, JsonValue, model_validator

from sirenity.contexts.shared import BaseValue, SirenityError, SirenRelation, SirenScope


class SirenRelationship(BaseValue):
    """Describe a runtime relationship to another OpenAPI resource.

    A relationship targets either an entity or a collection through its required `scope`. Set
    `embedded` only for an entity relationship when related values should be included as a Siren
    embedded representation instead. `title` overrides the compiled title for this link or
    embedded representation.

    Use `path_values` to select and render a nested collection route. Capabilities must belong to
    the relationship's selected scope.

    ```python
    from sirenity import SirenRelationship, SirenScope

    relationship = SirenRelationship(
        rel=("collection",),
        resource="diagram",
        scope=SirenScope.COLLECTION,
        path_values={"diagram_set_id": diagram_set_id},
        capabilities=frozenset({"list_diagram_set_diagrams"}),
    )
    ```
    """

    rel: tuple[SirenRelation, ...] = Field(min_length=1)
    resource: str
    scope: SirenScope
    title: str | None = None
    value: Mapping[str, JsonValue] = Field(default_factory=dict)
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    capabilities: frozenset[str] = frozenset()
    embedded: bool = False

    @model_validator(mode="after")
    def validate_scope(self) -> "SirenRelationship":
        if self.scope == SirenScope.ROOT:
            raise SirenityError(
                "Siren relationship scope must be entity or collection")
        if self.scope == SirenScope.COLLECTION and self.embedded:
            raise SirenityError(
                "Siren collection relationships cannot be embedded")
        return self
