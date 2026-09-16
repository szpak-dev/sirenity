from ...graph import SirenApi, SirenInput
from ...shared import BaseState, SirenityError
from ..document.values.document import SirenDocument
from ..projection.services.projection import SirenProjectionService
from ..projection.services.response import SirenResponseProjectionService
from ..projection.values.response import SirenProjectedResponse
from ..request.values.context import SirenContext
from ..request.values.response import SirenResponseContext


class SirenEngine(BaseState):
    api: SirenApi
    projection: SirenProjectionService
    response_projection: SirenResponseProjectionService

    def project(self, context: SirenContext) -> SirenDocument:
        return self.projection.project(self.api, context)

    def project_response(self, context: SirenResponseContext) -> SirenDocument:
        return self.response_projection.project(self.api, context)

    def project_response_result(self, context: SirenResponseContext) -> SirenProjectedResponse:
        return self.response_projection.project_result(self.api, context)

    def has_response(self, context: SirenResponseContext) -> bool:
        return self.response_projection.has_response(self.api, context)

    def project_error(self, context: SirenResponseContext, request_url: str | None = None) -> SirenDocument:
        return self.response_projection.project_error(self.api, context, request_url)

    def operation_input(self, operation_id: str) -> SirenInput | None:
        matches = [operation for operation in self.api.operations if operation.name == operation_id]
        if len(matches) != 1:
            raise SirenityError(f"Siren input references unknown operation: {operation_id}")
        return matches[0].input
