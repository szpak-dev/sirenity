from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue


class SirenCapability(BaseValue):
    definition: str
    schema_: Mapping[str, JsonValue] = Field(alias="schema", serialization_alias="schema")

    @property
    def schema(self) -> Mapping[str, JsonValue]:
        return self.schema_
