from __future__ import annotations

from pydantic import Field

from ....shared import SirenRelation
from .embedded_link import SirenEmbeddedLink
from .entity import SirenEntity


class SirenEmbeddedRepresentation(SirenEntity):
    rel: tuple[SirenRelation, ...] = Field(min_length=1)
    entities: tuple[SirenEmbeddedLink | SirenEmbeddedRepresentation, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
