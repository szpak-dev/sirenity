from ....shared import BaseValue
from .operation_draft import OperationDraft
from .resource import Resource


class NormalizedOpenApi(BaseValue):
    root_path: str = "/"
    root_title: str = ""
    root_version: str = ""
    resources: tuple[Resource, ...] = ()
    operations: tuple[OperationDraft, ...] = ()
    root_operations: tuple[str, ...] = ()
