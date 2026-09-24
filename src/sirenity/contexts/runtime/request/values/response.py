from collections.abc import Mapping
from typing import Literal

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
    result: JsonValue
    base_url: str
    title: str = ""
    media_type: Literal[""] | SirenMediaType = ""
    representation: Literal[""] | SirenRepresentation = ""
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    query: tuple[tuple[str, JsonValue], ...] = ()
    body: JsonValue = Field(default_factory=dict)
    capabilities: frozenset[str] = frozenset()
    navigation_capabilities: frozenset[str] = frozenset()
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
