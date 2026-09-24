from collections.abc import Mapping

from pydantic import Field

from ....shared import BaseValue
from .route import SirenRoute


class SirenResource(BaseValue):
    reference: str
    name: str
    resource_class: str
    path_bindings: Mapping[str, tuple[str, ...]]
    title: str = ""
    identifier: str = "id"
    collection: SirenRoute
    entity: SirenRoute = Field(default_factory=lambda: SirenRoute(path=""))
    collection_operations: tuple[str, ...] = ()
    entity_operations: tuple[str, ...] = ()
