from collections.abc import Mapping

from pydantic import Field, JsonValue, model_validator

from ....shared import (
    BaseValue,
    SirenityError,
    SirenMediaType,
    SirenRepresentation,
)
from .relationship import SirenRelationship


class SirenResponseContext(BaseValue):
    operation_id: str
    status: int
    result: JsonValue = None
    base_url: str
    title: str | None = None
    media_type: SirenMediaType | None = None
    representation: SirenRepresentation | None = None
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    query: tuple[tuple[str, JsonValue], ...] = ()
    capabilities: frozenset[str] = frozenset()
    item_titles: tuple[str, ...] = ()
    item_capabilities: tuple[frozenset[str], ...] = ()
    relationships: tuple[SirenRelationship, ...] = ()

    @model_validator(mode="after")
    def validate_response(self) -> "SirenResponseContext":
        if not 100 <= self.status <= 599:
            raise SirenityError("Siren response status must be between 100 and 599")
        if self.item_titles and len(self.item_titles) != len(self.result):
            raise SirenityError("Siren item titles must align with response items")
        if self.item_capabilities and len(self.item_capabilities) != len(self.result):
            raise SirenityError("Siren item capabilities must align with response items")
        return self
