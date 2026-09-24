from collections.abc import Mapping

from pydantic import Field, JsonValue, model_validator

from ....shared import BaseValue, SirenityError, SirenScope
from .relationship import SirenRelationship


class SirenContext(BaseValue):
    base_url: str
    scope: SirenScope = SirenScope.ENTITY
    resource: str = ""
    title: str = ""
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
        if self.scope == SirenScope.ROOT and self.resource:
            raise SirenityError("Siren root context cannot declare a resource")
        if self.scope != SirenScope.ROOT and not self.resource:
            raise SirenityError(f"Siren {self.scope} context requires a resource")
        if self.item_titles and len(self.item_titles) != len(self.items):
            raise SirenityError("Siren item titles must align with collection items")
        if self.item_capabilities and len(self.item_capabilities) != len(self.items):
            raise SirenityError("Siren item capabilities must align with collection items")
        return self
