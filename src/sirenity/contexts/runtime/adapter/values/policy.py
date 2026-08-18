from typing import Literal

from pydantic import model_validator

from sirenity.contexts.runtime.request import SirenRelationship
from sirenity.contexts.shared import BaseValue, SirenityError


class SirenAdapterPolicy(BaseValue):
    """Declare application-owned authorization and optional projection overrides.

    Adapters never infer permissions from OpenAPI or result identifiers. Representation defaults come
    from the compiled API graph and may be overridden for exceptional operations. For a collection
    response, `item_titles` supplies one explicit title per result item in the same order as
    `item_capabilities`.
    """

    title: str | None = None
    representation: Literal["root", "entity",
                            "collection", "command"] | None = None
    capabilities: frozenset[str] = frozenset()
    all_capabilities: bool = False
    item_titles: tuple[str, ...] = ()
    item_capabilities: tuple[frozenset[str], ...] = ()
    relationships: tuple[SirenRelationship, ...] = ()

    @model_validator(mode="after")
    def validate_capabilities(self) -> "SirenAdapterPolicy":
        if self.all_capabilities and self.capabilities:
            raise SirenityError(
                "Siren adapter policy cannot combine all capabilities with explicit capabilities"
            )
        return self
