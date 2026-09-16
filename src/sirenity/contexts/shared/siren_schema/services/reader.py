from copy import deepcopy
from dataclasses import dataclass
from importlib.resources import files

from pydantic import JsonValue, TypeAdapter
from wireup import injectable

from ..values.document import SirenSchemaDocument


@injectable
@dataclass(frozen=True)
class SirenSchemaReader:
    """Load the pinned official Siren schema as an immutable document."""

    def document(self) -> SirenSchemaDocument:
        source = files("sirenity.contexts.shared.siren_schema.values").joinpath("siren.schema.json")
        return SirenSchemaDocument(value=TypeAdapter(dict[str, JsonValue]).validate_json(source.read_text()))

    def freeze(self, value: JsonValue) -> JsonValue:
        return deepcopy(value)
