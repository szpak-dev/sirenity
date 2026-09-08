import json
from collections.abc import Mapping
from typing import Any

from ..shared import SirenContractError


def normalized_openapi(openapi: Mapping[str, Any]) -> dict[str, Any]:
    paths = openapi.get("paths", {})
    if not isinstance(paths, Mapping):
        paths = {}
    for path, path_item in paths.items():
        if not isinstance(path_item, Mapping):
            continue
        for method, operation in path_item.items():
            if not isinstance(operation, Mapping):
                continue
            responses = operation.get("responses")
            if not isinstance(responses, Mapping):
                continue
            statuses: set[str] = set()
            for status in responses:
                normalized = str(status)
                if normalized in statuses:
                    escaped_path = str(path).replace("~", "~0").replace("/", "~1")
                    escaped_method = str(method).replace("~", "~0").replace("/", "~1")
                    location = (
                        f"#/paths/{escaped_path}/"
                        f"{escaped_method}/responses"
                    )
                    raise SirenContractError(
                        location,
                        "input",
                        f"OpenAPI operation declares duplicate response status: {normalized}",
                    )
                statuses.add(normalized)
    try:
        return json.loads(json.dumps(openapi))
    except Exception as error:
        raise SirenContractError(
            "#", "input", "OpenAPI document must be JSON-compatible."
        ) from error
