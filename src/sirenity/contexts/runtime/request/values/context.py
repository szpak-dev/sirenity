from collections.abc import Mapping

from pydantic import Field, JsonValue, model_validator

from ....shared import BaseValue, SirenityError, SirenScope
from .relationship import SirenRelationship


class SirenContext(BaseValue):
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
            raise SirenityError("Siren root context cannot declare a resource")
        if self.scope != SirenScope.ROOT and self.resource is None:
            raise SirenityError(f"Siren {self.scope} context requires a resource")
        if self.item_titles and len(self.item_titles) != len(self.items):
            raise SirenityError("Siren item titles must align with collection items")
        if self.item_capabilities and len(self.item_capabilities) != len(self.items):
            raise SirenityError("Siren item capabilities must align with collection items")
        return self
