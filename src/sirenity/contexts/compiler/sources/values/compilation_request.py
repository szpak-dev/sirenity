from pydantic import JsonValue

from ....shared import BaseValue


class OpenApiCompilationRequest(BaseValue):
    document: dict[str, JsonValue]
    paths: dict[str, JsonValue]
    source_path: str
    public_path: str
