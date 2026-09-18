from ....shared import BaseValue
from ...specification import SirenRequirement


class SirenFinding(BaseValue):
    requirement: SirenRequirement
    implemented: bool
    evidence: str
