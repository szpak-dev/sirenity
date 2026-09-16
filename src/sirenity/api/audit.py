"""Compatibility audit.

<!-- docs:order=60 -->
"""

import json
from collections.abc import Mapping

from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError
from pydantic import JsonValue, TypeAdapter, ValidationError

from ..contexts.compiler import SirenApiService
from ..contexts.compiler.compatibility import SirenCompatibilityReport
from ..contexts.shared import SirenContractError
from ..wiring import application


def audit(openapi: Mapping[str, JsonValue]) -> SirenCompatibilityReport:
    """Inspect a valid OpenAPI document against the current official-Siren support boundary.

    Call this during startup before `siren(openapi)` when a consumer needs every currently
    unsupported construct at once. The report exposes typed findings and `render()` for terminal
    or CI output; `siren(openapi)` remains the strict fail-fast compilation entry point.
    """

    try:
        document = TypeAdapter(dict[str, JsonValue]).validate_json(json.dumps(openapi))
    except (TypeError, ValueError, ValidationError) as error:
        raise SirenContractError("#", "input", "OpenAPI document must be JSON-compatible.") from error
    try:
        validate(document)
    except OpenAPIValidationError as error:
        raise SirenContractError(
            "#", "openapi", "OpenAPI document does not conform to OpenAPI 3.1."
        ) from error
    service = application.container.get(SirenApiService)
    document = service.normalize(openapi)
    return service.audit(document)
