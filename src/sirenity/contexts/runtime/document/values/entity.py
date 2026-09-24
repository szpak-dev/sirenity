from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, JsonValue

from ....shared import BaseValue
from .action import SirenAction
from .link import SirenLink


class SirenEntity(BaseValue):
    class_: tuple[str, ...] = Field(default=(), alias="class", exclude_if=lambda value: not value)
    title: str = Field(default="", exclude_if=lambda value: not value)
    properties: Mapping[str, JsonValue] = Field(default_factory=dict, exclude_if=lambda value: not value)
    actions: tuple[SirenAction, ...] = Field(default=(), exclude_if=lambda value: not value)
    links: tuple[SirenLink, ...] = Field(default=(), exclude_if=lambda value: not value)
