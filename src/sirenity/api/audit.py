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

    ### Run the compatibility gate

    Call this during startup before `siren(openapi)` when a consumer needs every currently
    unsupported construct at once. The report exposes typed findings and `render()` for terminal
    or CI output; `siren(openapi)` remains the strict fail-fast compilation entry point.

    ```python
    from sirenity import audit

    report = audit(openapi)
    if not report.compatible:
        raise SystemExit(report.render())
    ```

    A zero exit proves that the supplied JSON-compatible OpenAPI 3.1 document fits the current
    compilation boundary. It does not validate application authorization, operation execution, or
    business behavior.

    ### Support and maturity boundary

    Sirenity requires Python 3.12 or later and currently declares development status Alpha. The
    supported Python surface is the set of names exported from `sirenity`; private compiler and
    runtime modules are not compatibility contracts. Default documents use official Siren members.
    Optional profiles own their explicitly versioned extension metadata.

    Run this audit and the consumer's public-behavior suite when upgrading Sirenity. A compatible
    report establishes contract coverage for compilation, while successful application tests remain
    the evidence for policy and execution behavior.
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
