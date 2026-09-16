from dataclasses import dataclass

from pydantic import BaseModel
from wireup import injectable

from ....shared.siren_schema import SirenSchemaReader
from ..values.capability import SirenCapability


@injectable
@dataclass(frozen=True)
class SirenSerializationSchemaExporter:
    schemas: SirenSchemaReader

    def export(self, definition: str, model: type[BaseModel]) -> SirenCapability:
        schema = model.model_json_schema(by_alias=True, mode="serialization")
        reference = schema.get("$ref")
        if reference is None:
            return SirenCapability(definition=definition, schema=self.schemas.freeze(schema))
        resolved = schema
        for segment in reference.removeprefix("#/").split("/"):
            resolved = resolved[segment]
        return SirenCapability(
            definition=definition,
            schema=self.schemas.freeze({**resolved, "$defs": schema.get("$defs", {})}),
        )
