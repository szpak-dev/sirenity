from typing import Any, ClassVar

from pydantic_core import CoreSchema, core_schema

from sirenity.contexts.shared import SirenityError

from .uri import SirenUri


class SirenRelation(str):
    """Represent an official Siren relation value."""

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
    def __get_pydantic_core_schema__(cls, source_type: object, handler: Any) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls.validate, core_schema.str_schema())

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: Any) -> dict[str, Any]:
        return cls.schema()

    @classmethod
    def validate(cls, value: str) -> "SirenRelation":
        if value in cls.registered():
            return cls(value)
        try:
            SirenUri.validate(value)
        except SirenityError as error:
            message = "Siren relation must be an official relation token or URI."
            raise SirenityError(message) from error
        return cls(value)

    @classmethod
    def registered(cls) -> frozenset[str]:
        return frozenset(cls.registered_values)

    @classmethod
    def schema(cls) -> dict[str, Any]:
        return {
            "anyOf": [
                {"format": "uri", "type": "string"},
                {"enum": list(cls.registered_values), "type": "string"},
            ]
        }
