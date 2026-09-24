from dataclasses import dataclass

from .follow_up import SirenFollowUp


@dataclass(frozen=True, kw_only=True)
class SirenItemFollowUp(SirenFollowUp):
    """Declare one safe read target for every item in a paginated response.

    ``item_collection`` names the top-level response property containing the items. Inherited
    ``parameters`` map target path or query arguments to required, non-null item properties.
    """

    item_collection: str
