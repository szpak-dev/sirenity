from sirenity.contexts.shared import BaseValue

from .operation_draft import OperationDraft
from .resource import Resource


class NormalizedOpenApi(BaseValue):
    """Immutable source model awaiting graph-wide link validation."""

    root_path: str = "/"
    root_title: str = ""
    root_version: str = ""
    resources: tuple[Resource, ...] = ()
    operations: tuple[OperationDraft, ...] = ()
    root_operations: tuple[str, ...] = ()
