import re
from typing import Any, ClassVar

from pydantic_core import CoreSchema, core_schema

from sirenity.contexts.shared import SirenityError


class SirenMediaType(str):
    """Represent an official Siren media type."""

    default_value: ClassVar[str] = "application/x-www-form-urlencoded"
    pattern: ClassVar[str] = (
        r"""^(application|audio|image|message|model|multipart|text|video)\/"""
        r"""([A-Z]|[a-z]|[0-9]|[\!\#\$\&\.\+\-\^\_]){1,127}"""
        r"""(; ?(([\!\#\$\%\&\'\(\)\*\+-\.\/]|[0-9]|[A-Z]|"""
        r"""[\^\_\`\]\|]|[a-z]|[\|\~])+)+=((([\!\#\$\%\&\'\(\)\*\+-\.\/]|"""
        r"""[0-9]|[A-Z]|[\^\_\`\]\|]|[a-z]|[\|\~])+)|"([\!\#\$\%\&\.\(\)\*\+\,\-\.\/]|"""
        r"""[0-9]|[\:\;\<\=\>\?\@]|[A-Z]|[\[\\\]\^\_\`]|[a-z]|[\{\|\}\~])+"))*$"""
    )

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: object, handler: Any) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: Any) -> dict[str, Any]:
        return cls.schema()

    @classmethod
    def validate(cls, value: str) -> "SirenMediaType":
        if re.fullmatch(cls.schema()["pattern"], value) is None:
            message = "Siren media type must use the official media-type grammar."
            raise SirenityError(message)
        return cls(value)

    @classmethod
    def default(cls) -> "SirenMediaType":
        return cls.validate(cls.default_value)

    @classmethod
    def schema(cls) -> dict[str, Any]:
        return {
            "description": (
                "Defines media type of the linked resource, per Web Linking (RFC5988). For the syntax, see "
                "RFC2045 (section 5.1), RFC4288 (section 4.2), RFC6838 (section 4.2)"
            ),
            "pattern": cls.pattern,
            "type": "string",
        }
