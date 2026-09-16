from ....shared import BaseValue
from .route import SirenRoute


class SirenRoot(BaseValue):
    route: SirenRoute = SirenRoute(path="/")
    title: str = ""
    version: str = ""
    operations: tuple[str, ...] = ()
