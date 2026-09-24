from __future__ import annotations

from pydantic import Field, model_validator

from ....shared import SirenityError
from .embedded_link import SirenEmbeddedLink
from .embedded_representation import SirenEmbeddedRepresentation
from .entity import SirenEntity


class SirenDocument(SirenEntity):
    entities: tuple[SirenEmbeddedLink | SirenEmbeddedRepresentation, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )

    @model_validator(mode="after")
    def validate_action_names(self) -> SirenDocument:
        actions = self.actions or ()
        if len({action.name for action in actions}) != len(actions):
            raise SirenityError("Siren document action names must be unique.")
        return self
