from dataclasses import dataclass

from wireup import injectable

from sirenity.contexts.graph import SirenApi

from ...projection import SirenProjectionService, SirenResponseProjectionService
from ..state import SirenEngine


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
