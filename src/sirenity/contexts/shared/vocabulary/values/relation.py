from typing import ClassVar, Self

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from .uri import SirenUri


class SirenRelation(str):
    registered_values: ClassVar[tuple[str, ...]] = (
        "about",
        "alternate",
        "appendix",
        "archives",
        "author",
        "blocked-by",
        "bookmark",
        "canonical",
        "chapter",
        "collection",
        "contents",
        "convertedFrom",
        "copyright",
        "create-form",
        "current",
        "derivedfrom",
        "describedby",
        "describes",
        "disclosure",
        "dns-prefetch",
        "duplicate",
        "edit",
        "edit-form",
        "edit-media",
        "enclosure",
        "first",
        "glossary",
        "help",
        "hosts",
        "hub",
        "icon",
        "index",
        "item",
        "last",
        "latest-version",
        "license",
        "lrdd",
        "memento",
        "monitor",
        "monitor-group",
        "next",
        "next-archive",
        "nofollow",
        "noreferrer",
        "original",
        "payment",
        "pingback",
        "preconnect",
        "predecessor-version",
        "prefetch",
        "preload",
        "prerender",
        "prev",
        "preview",
        "previous",
        "prev-archive",
        "privacy-policy",
        "profile",
        "related",
        "restconf",
        "replies",
        "search",
        "section",
        "self",
        "service",
        "start",
        "stylesheet",
        "subsection",
        "successor-version",
        "tag",
        "terms-of-service",
        "timegate",
        "timemap",
        "type",
        "up",
        "version-history",
        "via",
        "webmention",
        "working-copy",
        "working-copy-of",
    )

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: type[Self], handler: GetCoreSchemaHandler) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        return cls.schema()

    @classmethod
    def validate(cls, value: str) -> "SirenRelation":
        if value in cls.registered():
            return cls(value)
        SirenUri.validate(value)
        return cls(value)

    @classmethod
    def registered(cls) -> frozenset[str]:
        return frozenset(cls.registered_values)

    @classmethod
    def schema(cls) -> JsonSchemaValue:
        return {
            "anyOf": [
                {"format": "uri", "type": "string"},
                {"enum": list(cls.registered_values), "type": "string"},
            ]
        }
