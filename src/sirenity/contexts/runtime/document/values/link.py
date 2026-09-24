from typing import Literal

from pydantic import Field

from ....shared import BaseValue, SirenMediaType, SirenRelation, SirenUri


class SirenLink(BaseValue):
    class_: tuple[str, ...] = Field(default=(), alias="class", exclude_if=lambda value: not value)
    title: str = Field(default="", exclude_if=lambda value: not value)
    rel: tuple[SirenRelation, ...] = Field(min_length=1)
    href: SirenUri
    type: Literal[""] | SirenMediaType = Field(default="", exclude_if=lambda value: not value)
