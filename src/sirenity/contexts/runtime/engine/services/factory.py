from dataclasses import dataclass

from wireup import injectable

from ....graph import SirenApi
from ...projection.services.projection import SirenProjectionService
from ...projection.services.response import SirenResponseProjectionService
from ..engine import SirenEngine


@injectable
@dataclass(frozen=True)
class SirenEngineFactory:
    projection: SirenProjectionService
    response_projection: SirenResponseProjectionService

    def create(self, api: SirenApi) -> SirenEngine:
        return SirenEngine(
            api=api,
            projection=self.projection,
            response_projection=self.response_projection,
        )
