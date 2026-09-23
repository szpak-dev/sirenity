from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SirenSourceInput:
    """Select one required, non-null source-request input for typed navigation.

    ``location`` identifies the source operation's ``path``, ``query``, or JSON ``body`` input.
    ``name`` identifies that input within the declared location. The compiler requires the source
    and target schemas to match and propagates no undeclared source input.
    """

    location: Literal["path", "query", "body"]
    name: str
