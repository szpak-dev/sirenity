from typing import ClassVar

from pydantic import Field, model_validator
from pydantic.json_schema import SkipJsonSchema

from sirenity.contexts.shared import BaseValue, SirenActionMethod, SirenityError, SirenMediaType, SirenUri

from .field import SirenField


class SirenAction(BaseValue):
    """Describe an available Siren action."""

    default_media_type: ClassVar[SirenMediaType] = SirenMediaType.default()
    class_: tuple[str, ...] | None = Field(default=None, alias="class")
    name: str
    method: SirenActionMethod = SirenActionMethod.default()
    href: SirenUri
    title: str | None = None
    type: SirenMediaType | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra={"default": default_media_type})
    fields: tuple[SirenField, ...] | None = None

    @model_validator(mode="after")
    def apply_default_media_type(self) -> "SirenAction":
        if self.fields is not None and self.type is None:
            object.__setattr__(self, "type", self.default_media_type)
        return self

    @model_validator(mode="after")
    def validate_field_names(self) -> "SirenAction":
        fields = self.fields or ()
        if len({field.name for field in fields}) != len(fields):
            raise SirenityError("Siren action field names must be unique.")
        return self
