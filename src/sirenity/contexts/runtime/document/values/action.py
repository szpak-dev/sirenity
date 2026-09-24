from typing import ClassVar, Literal

from pydantic import Field, model_validator

from ....shared import BaseValue, SirenActionMethod, SirenityError, SirenMediaType, SirenUri
from .field import SirenField


class SirenAction(BaseValue):
    default_media_type: ClassVar[SirenMediaType] = SirenMediaType.default()
    class_: tuple[str, ...] = Field(default=(), alias="class", exclude_if=lambda value: not value)
    name: str
    method: SirenActionMethod = SirenActionMethod.default()
    href: SirenUri
    title: str = Field(default="", exclude_if=lambda value: not value)
    type: Literal[""] | SirenMediaType = Field(
        default="", exclude_if=lambda value: not value, json_schema_extra={"default": default_media_type}
    )
    fields: tuple[SirenField, ...] = Field(default=(), exclude_if=lambda value: not value)

    @model_validator(mode="after")
    def apply_default_media_type(self) -> "SirenAction":
        if self.fields and not self.type:
            object.__setattr__(self, "type", self.default_media_type)
        return self

    @model_validator(mode="after")
    def validate_field_names(self) -> "SirenAction":
        fields = self.fields or ()
        if len({field.name for field in fields}) != len(fields):
            raise SirenityError("Siren action field names must be unique.")
        return self
