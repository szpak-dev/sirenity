from typing import ClassVar

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer, model_validator

from ....shared import BaseValue, SirenActionMethod, SirenityError, SirenMediaType, SirenUri
from .field import SirenField


class SirenAction(BaseValue):
    default_media_type: ClassVar[SirenMediaType] = SirenMediaType.default()
    class_: tuple[str, ...] = Field(default=(), alias="class", exclude_if=lambda value: not value)
    name: str
    method: SirenActionMethod = SirenActionMethod.default()
    href: SirenUri
    title: str = Field(default="", exclude_if=lambda value: not value)
    type: SirenMediaType = Field(
        default_factory=SirenMediaType.default, json_schema_extra={"default": default_media_type}
    )
    fields: tuple[SirenField, ...] = Field(default=(), exclude_if=lambda value: not value)

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler):
        payload: dict[str, object] = handler(self)
        if not self.fields and not self.supplies("type"):
            payload.pop("type", None)
        return payload

    @model_validator(mode="after")
    def validate_field_names(self) -> "SirenAction":
        fields = self.fields or ()
        if len({field.name for field in fields}) != len(fields):
            raise SirenityError("Siren action field names must be unique.")
        return self
