from pydantic import model_validator

from ...shared import BaseValue, SirenityError, SirenRepresentation
from ..request import SirenRelationship


class SirenAdapterPolicy(BaseValue):
    title: str | None = None
    representation: SirenRepresentation | None = None
    capabilities: frozenset[str] = frozenset()
    all_capabilities: bool = False
    item_titles: tuple[str, ...] = ()
    item_capabilities: tuple[frozenset[str], ...] = ()
    relationships: tuple[SirenRelationship, ...] = ()

    @model_validator(mode="after")
    def validate_capabilities(self) -> "SirenAdapterPolicy":
        if self.all_capabilities and self.capabilities:
            raise SirenityError("Siren adapter policy cannot combine all capabilities with explicit capabilities")
        return self
