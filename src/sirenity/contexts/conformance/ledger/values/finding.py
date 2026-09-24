from ....shared import BaseValue
from ... import SirenRequirement


class SirenFinding(BaseValue):
    requirement: SirenRequirement
    implemented: bool
    evidence: str
