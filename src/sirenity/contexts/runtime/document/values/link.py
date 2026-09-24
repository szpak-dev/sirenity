from pydantic import Field, SerializerFunctionWrapHandler, model_serializer

from ....shared import BaseValue, SirenMediaType, SirenRelation, SirenUri


class SirenLink(BaseValue):
    class_: tuple[str, ...] = Field(default=(), alias="class", exclude_if=lambda value: not value)
    title: str = Field(default="", exclude_if=lambda value: not value)
    rel: tuple[SirenRelation, ...] = Field(min_length=1)
    href: SirenUri
    type: SirenMediaType = Field(default_factory=SirenMediaType.default)

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler):
        payload: dict[str, object] = handler(self)
        if not self.supplies("type"):
            payload.pop("type", None)
        return payload
