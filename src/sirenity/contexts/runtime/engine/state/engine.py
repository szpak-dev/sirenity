from sirenity.contexts.graph import SirenApi, SirenInput
from sirenity.contexts.shared import BaseState, SirenityError

from ...document import SirenDocument
from ...projection import SirenProjectionService, SirenResponseProjectionService
from ...request import SirenContext, SirenResponseContext


class SirenEngine(BaseState):
    api: SirenApi
    projection: SirenProjectionService
    response_projection: SirenResponseProjectionService

    def project(self, context: SirenContext) -> SirenDocument:
        try:
            return self.projection.project(self.api, context)
        except Exception as error:
            raise SirenityError(f"Siren projection failed: {error}") from error

    def project_response(self, context: SirenResponseContext) -> SirenDocument:
        try:
            return self.response_projection.project(self.api, context)
        except Exception as error:
            raise SirenityError("Siren response projection failed") from error

    def has_response(self, context: SirenResponseContext) -> bool:
        try:
            return self.response_projection.has_response(self.api, context)
        except Exception as error:
            raise SirenityError("Siren response lookup failed") from error

    def project_error(
        self, context: SirenResponseContext, request_url: str | None = None
    ) -> SirenDocument:
        try:
            return self.response_projection.project_error(self.api, context, request_url)
        except Exception as error:
            raise SirenityError("Siren error projection failed") from error

    def operation_input(self, operation_id: str) -> SirenInput | None:
        try:
            matches = [
                operation for operation in self.api.operations if operation.name == operation_id]
            if len(matches) != 1:
                raise SirenityError(
                    f"Siren input references unknown operation: {operation_id}")
            return matches[0].input
        except Exception as error:
            raise SirenityError(
                "Siren operation input lookup failed") from error
