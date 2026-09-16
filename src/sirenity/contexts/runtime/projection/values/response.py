from ....shared import BaseValue
from ...document.values.document import SirenDocument
from .continuation import SirenProjectedContinuation


class SirenProjectedResponse(BaseValue):
    document: SirenDocument
    continuations: tuple[SirenProjectedContinuation, ...] = ()
