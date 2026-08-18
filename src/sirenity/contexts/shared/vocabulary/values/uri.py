from typing import Any, ClassVar

from jsonschema import FormatChecker
from pydantic_core import CoreSchema, core_schema

from sirenity.contexts.shared import SirenityError


class SirenUri(str):
    """Represent an official Siren URI value."""

    checker: ClassVar[FormatChecker] = FormatChecker()

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: object, handler: Any) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: Any) -> dict[str, str]:
        return {"format": "uri", "type": "string"}

    @classmethod
    def validate(cls, value: str) -> "SirenUri":
        if not cls.checker.conforms(value, "uri"):
            message = "Siren URI must be a valid URI."
            raise SirenityError(message)
        return cls(value)
