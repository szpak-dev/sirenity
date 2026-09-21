from ....shared import BaseValue
from ...document import SirenDocument
from .continuation import SirenProjectedContinuation
from .follow_up import SirenProjectedFollowUp
from .verification import SirenProjectedVerification


class SirenProjectedResponse(BaseValue):
    document: SirenDocument
    continuations: tuple[SirenProjectedContinuation, ...] = ()
    verifications: tuple[SirenProjectedVerification, ...] = ()
    follow_ups: tuple[SirenProjectedFollowUp, ...] = ()
