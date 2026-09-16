from typing import ClassVar, Self

from jsonschema import FormatChecker
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import CoreSchema, core_schema

from ... import SirenityError


class SirenUri(str):
    checker: ClassVar[FormatChecker] = FormatChecker()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: type[Self], handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> dict[str, str]:
        return {"format": "uri", "type": "string"}

    @classmethod
    def validate(cls, value: str) -> "SirenUri":
        if not cls.checker.conforms(value, "uri"):
            message = "Siren URI must be a valid URI."
            raise SirenityError(message)
        return cls(value)
