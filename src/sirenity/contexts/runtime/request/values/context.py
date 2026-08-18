from collections.abc import Mapping

from pydantic import Field, JsonValue, model_validator

from sirenity.contexts.shared import BaseValue, SirenityError, SirenScope

from .relationship import SirenRelationship


class SirenContext(BaseValue):
    """Supply runtime state used to project a Siren document.

    Use the default `"entity"` scope for one resource, `"collection"` for a list, and `"root"`
    for an API entry point. A resource is required outside root scope and is the singular name
    derived from the collection route: `"record"` for `/records`. If the same resource appears
    in multiple nested routes, `path_values` selects the route with matching parent parameters.

    | Field | Purpose |
    | --- | --- |
    | `base_url` | Public origin joined with OpenAPI paths. |
    | `scope` | `"root"`, `"collection"`, or `"entity"`. |
    | `resource` | Derived singular resource name; required outside root. |
    | `title` | Explicit document title overriding compiled OpenAPI metadata. |
    | `value` | Entity or root properties and entity path parameters. |
    | `items` | Entity mappings for a collection. |
    | `item_titles` | Optional explicit titles aligned with collection items. |
    | `item_capabilities` | Optional permitted operation IDs for each collection item. |
    | `relationships` | Linked or embedded related resources for this document. |
    | `path_values` | Missing path parameters, such as a parent resource ID or a root command target. |
    | `query` | Ordered query pairs for self and action links. |
    | `capabilities` | Permitted OpenAPI `operationId` values. |
    """

    base_url: str
    scope: SirenScope = SirenScope.ENTITY
    resource: str | None = None
    title: str | None = None
    value: Mapping[str, JsonValue] = Field(default_factory=dict)
    items: tuple[Mapping[str, JsonValue], ...] = ()
    item_titles: tuple[str, ...] = ()
    item_capabilities: tuple[frozenset[str], ...] = ()
    relationships: tuple[SirenRelationship, ...] = ()
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    query: tuple[tuple[str, JsonValue], ...] = ()
    capabilities: frozenset[str] = frozenset()
    action_bindings: Mapping[str, Mapping[str, str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope(self) -> "SirenContext":
        if self.scope == SirenScope.ROOT and self.resource is not None:
            raise SirenityError(
                "Siren root context cannot declare a resource")
        if self.scope != SirenScope.ROOT and self.resource is None:
            raise SirenityError(
                f"Siren {self.scope} context requires a resource")
        if any(isinstance(value, (dict, list)) for _, value in self.query):
            raise SirenityError("Siren query values must be scalar")
        if self.item_titles and len(self.item_titles) != len(self.items):
            raise SirenityError(
                "Siren item titles must align with collection items")
        if self.item_capabilities and len(self.item_capabilities) != len(self.items):
            raise SirenityError(
                "Siren item capabilities must align with collection items")
        return self
