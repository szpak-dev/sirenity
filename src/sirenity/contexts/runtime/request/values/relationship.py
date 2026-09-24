from collections.abc import Mapping

from pydantic import Field, JsonValue, model_validator

from ....shared import BaseValue, SirenityError, SirenRelation, SirenScope


class SirenRelationship(BaseValue):
    rel: tuple[SirenRelation, ...] = Field(min_length=1)
    resource: str
    scope: SirenScope
    title: str = ""
    value: Mapping[str, JsonValue] = Field(default_factory=dict)
    path_values: Mapping[str, JsonValue] = Field(default_factory=dict)
    capabilities: frozenset[str] = frozenset()
    embedded: bool = False

    @model_validator(mode="after")
    def validate_scope(self) -> "SirenRelationship":
        if self.scope == SirenScope.ROOT:
            raise SirenityError("Siren relationship scope must be entity or collection")
        if self.scope == SirenScope.COLLECTION and self.embedded:
            raise SirenityError("Siren collection relationships cannot be embedded")
        return self
