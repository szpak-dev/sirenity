from collections.abc import Mapping
from dataclasses import dataclass, field

from ..contexts.shared import SirenScope
from .source_input import SirenSourceInput


@dataclass(frozen=True)
class SirenFollowUp:
    """Declare one safe read target for :func:`siren_follow_ups`.

    ``parameters`` maps target path or query argument names to top-level response property names.
    Prefix an argument with ``path.`` or ``query.`` when its location is not otherwise unambiguous.
    ``rel`` and ``scope`` become the existing Siren relationship metadata on the generated OpenAPI
    Response Link Object. ``source_inputs`` maps target argument names to required source-request
    inputs; response-property parameters and source inputs must target distinct arguments.
    """

    operation_id: str
    parameters: Mapping[str, str]
    rel: str
    scope: SirenScope
    source_inputs: Mapping[str, SirenSourceInput] = field(default_factory=dict)
