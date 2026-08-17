from sirenity.contexts.graph import SirenApi
from sirenity.contexts.shared import BaseState, ModwireSirenError

from ...document import SirenDocument
from ...operation_input import SirenOperationInput, SirenOperationInputService
from ...projection import SirenProjectionService, SirenResponseProjectionService
from ...request import SirenContext, SirenResponseContext


class SirenEngine(BaseState):
    api: SirenApi
    projection: SirenProjectionService
    response_projection: SirenResponseProjectionService
    operation_inputs: SirenOperationInputService

    def project(self, context: SirenContext) -> SirenDocument:
        try:
            return self.projection.project(self.api, context)
        except Exception as error:
            raise ModwireSirenError(f"Siren projection failed: {error}") from error

    def project_response(self, context: SirenResponseContext) -> SirenDocument:
        try:
            return self.response_projection.project(self.api, context)
        except Exception as error:
            raise ModwireSirenError("Siren response projection failed") from error

    def has_response(self, context: SirenResponseContext) -> bool:
        try:
            return self.response_projection.has_response(self.api, context)
        except Exception as error:
            raise ModwireSirenError("Siren response lookup failed") from error

    def project_error(
        self, context: SirenResponseContext, request_url: str | None = None
    ) -> SirenDocument:
        try:
            return self.response_projection.project_error(self.api, context, request_url)
        except Exception as error:
            raise ModwireSirenError("Siren error projection failed") from error

    def operation_input(self, operation_id: str) -> SirenOperationInput | None:
        try:
            return self.operation_inputs.input(self.api, operation_id)
        except Exception as error:
            raise ModwireSirenError("Siren operation input lookup failed") from error
