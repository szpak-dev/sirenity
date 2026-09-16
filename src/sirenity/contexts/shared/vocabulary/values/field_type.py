from typing import ClassVar, Self

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticCustomError, core_schema


class SirenFieldType(str):
    default_value: ClassVar[str] = "text"
    official_values: ClassVar[tuple[str, ...]] = (
        "hidden",
        "text",
        "search",
        "tel",
        "url",
        "email",
        "password",
        "datetime",
        "date",
        "month",
        "week",
        "time",
        "datetime-local",
        "number",
        "range",
        "color",
        "checkbox",
        "radio",
        "file",
    )

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: type[Self], handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return cls.schema()

    @classmethod
    def default(cls) -> "SirenFieldType":
        return cls.validate(cls.default_value)

    @classmethod
    def values(cls) -> frozenset[str]:
        return frozenset(cls.official_values)

    @classmethod
    def validate(cls, value: str) -> "SirenFieldType":
        if value not in cls.values():
            raise PydanticCustomError("enum", "Siren field type must be an official HTML5 input type.")
        return cls(value)

    @classmethod
    def schema(cls) -> JsonSchemaValue:
        return {
            "default": cls.default_value,
            "description": "The input type of the field. This is a subset of the input types specified by HTML5.",
            "enum": list(cls.official_values),
            "type": "string",
        }
