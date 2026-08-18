from __future__ import annotations

from pydantic import model_validator

from sirenity.contexts.shared import SirenityError

from .embedded_link import SirenEmbeddedLink
from .embedded_representation import SirenEmbeddedRepresentation
from .entity import SirenEntity


class SirenDocument(SirenEntity):
    """Represent an official Siren entity document.

    Project an engine request into this immutable public value, then serialize it with
    `model_dump(by_alias=True, mode="json", exclude_none=True)` for an
    `application/vnd.siren+json` response. Navigation belongs in `links`; embedded sub-entities
    belong in `entities`.
    """

    entities: tuple[SirenEmbeddedLink |
                    SirenEmbeddedRepresentation, ...] | None = None

    @model_validator(mode="after")
    def validate_action_names(self) -> SirenDocument:
        actions = self.actions or ()
        if len({action.name for action in actions}) != len(actions):
            raise SirenityError("Siren document action names must be unique.")
        return self
