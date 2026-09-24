from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue


class SirenRequirement(BaseValue):
    definition: str
    member: str
    schema_: Mapping[str, JsonValue] = Field(alias="schema", serialization_alias="schema")
    required: bool
    document: Mapping[str, JsonValue]
    enum_value: str | int | float | bool = ""

    @property
    def schema(self) -> Mapping[str, JsonValue]:
        return self.schema_

    @property
    def label(self) -> str:
        if not self.supplies("enum_value"):
            return f"{self.definition}.{self.member}"
        return f"{self.definition}.{self.member}.{self.enum_value}"
