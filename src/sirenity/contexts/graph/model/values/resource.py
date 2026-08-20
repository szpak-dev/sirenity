from sirenity.contexts.shared import BaseValue

from .route import SirenRoute


class SirenResource(BaseValue):
    reference: str
    name: str
    resource_class: str
    title: str | None = None
    identifier: str = "id"
    collection: SirenRoute
    entity: SirenRoute | None = None
    collection_operations: tuple[str, ...] = ()
    entity_operations: tuple[str, ...] = ()
