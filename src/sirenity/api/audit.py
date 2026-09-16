"""Compatibility audit.

<!-- docs:order=60 -->
"""

from collections.abc import Mapping

from openapi_spec_validator import validate
from pydantic import JsonValue

from ..contexts.compiler import SirenApiService
from ..contexts.compiler.compatibility import SirenCompatibilityReport
from ..wiring import application


def audit(openapi: Mapping[str, JsonValue]) -> SirenCompatibilityReport:
    """Inspect a valid OpenAPI document against the current official-Siren support boundary.

    Call this during startup before `siren(openapi)` when a consumer needs every currently
    unsupported construct at once. The report exposes typed findings and `render()` for terminal
    or CI output; `siren(openapi)` remains the strict fail-fast compilation entry point.
    """

    service = application.container.get(SirenApiService)
    document = service.normalize(openapi)
    validate(document)
    return service.audit(document)
