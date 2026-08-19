from collections.abc import Mapping

from pydantic import Field, JsonValue, model_validator

from sirenity.contexts.shared import (
    BaseValue,
    SirenityError,
    SirenMediaType,
    SirenRepresentation,
)

from .relationship import SirenRelationship


class SirenResponseContext(BaseValue):
    """Supply an executed OpenAPI operation and result for operation-aware projection.

    The compiled response status, media type, and schema determine whether the result is empty,
    an object, or an array. Array responses project as collections and object responses from an
    entity's or collection's exact route project as entities, an exact root operation projects as
    the API entry point, and other object responses project as command results. Set `representation`
    to override an exceptional operation. Root projection preserves executed mapping properties while
    compiled OpenAPI version metadata wins a `version` collision. `title` overrides the compiled
    resource or operation title. For an array response, `item_titles` supplies one explicit title per
    result item.
    """

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
            raise SirenityError(
                "Siren response status must be between 100 and 599")
        if any(isinstance(value, (dict, list)) for _, value in self.query):
            raise SirenityError("Siren query values must be scalar")
        if self.item_titles and (
            not isinstance(self.result, list) or len(
                self.item_titles) != len(self.result)
        ):
            raise SirenityError(
                "Siren item titles must align with response items")
        if self.item_capabilities and (
            not isinstance(self.result, list) or len(
                self.item_capabilities) != len(self.result)
        ):
            raise SirenityError(
                "Siren item capabilities must align with response items")
        return self
