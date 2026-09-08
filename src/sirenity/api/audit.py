"""Compatibility audit.

<!-- docs:order=60 -->
"""

from collections.abc import Mapping
from typing import Any

from openapi_spec_validator import validate

from ..contexts.compiler import SirenApiService
from ..contexts.compiler.compatibility import SirenCompatibilityReport
from ..contexts.compiler.document import normalized_openapi
from ..contexts.shared import SirenContractError
from ..wiring import application


def audit(openapi: Mapping[str, Any]) -> SirenCompatibilityReport:
    """Inspect a valid OpenAPI document against the current official-Siren support boundary.

    Call this during startup before `siren(openapi)` when a consumer needs every currently
    unsupported construct at once. The report exposes typed findings and `render()` for terminal
    or CI output; `siren(openapi)` remains the strict fail-fast compilation entry point.
    """

    if not isinstance(openapi, Mapping):
        raise SirenContractError("#", "input", "OpenAPI document must be a mapping.")
    document = normalized_openapi(openapi)
    try:
        validate(document)
    except Exception as error:
        raise SirenContractError("#", "openapi", "OpenAPI document does not conform to OpenAPI 3.1.") from error
    return application.container.get(SirenApiService).audit(document)
