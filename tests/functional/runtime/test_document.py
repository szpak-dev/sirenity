import pytest
from pydantic import ValidationError

from sirenity import (
    SirenAction,
    SirenDocument,
    SirenEmbeddedLink,
    SirenEmbeddedRepresentation,
    SirenField,
    SirenFieldValue,
    SirenLink,
)


class TestDocument:
    @pytest.mark.parametrize(
        ("value", "member"),
        [
            (SirenDocument(), "unknown"),
            (SirenAction(name="create", href="https://api.example.com/records"), "unknown"),
            (SirenField(name="title"), "required"),
            (SirenFieldValue(value="public"), "unknown"),
            (SirenLink(rel=("self",), href="https://api.example.com/records"), "unknown"),
            (SirenEmbeddedLink(rel=("item",), href="https://api.example.com/records/42"), "unknown"),
            (SirenEmbeddedRepresentation(rel=("item",)), "unknown"),
        ],
    )
    def test_public_document_values_reject_unknown_members(self, value, member):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            type(value)(**{**value.model_dump(), member: True})


    @pytest.mark.parametrize(
        "value",
        [
            SirenLink(rel=("self",), href="https://api.example.com/records"),
            SirenEmbeddedLink(rel=("item",), href="https://api.example.com/records/42"),
            SirenEmbeddedRepresentation(rel=("item",)),
        ],
    )
    def test_linked_and_embedded_entities_require_a_non_empty_relation(self, value):
        with pytest.raises(ValidationError, match="at least 1 item"):
            type(value)(**{**value.model_dump(), "rel": ()})


    def test_public_document_values_are_immutable(self):
        document = SirenDocument(title="Records")

        with pytest.raises(ValidationError, match="frozen"):
            document.title = "Other"


    def test_public_document_values_serialize_to_official_siren_shapes(self):
        document = SirenDocument(
            class_=("collection",),
            title="Records",
            properties={"count": 1},
            entities=(
                SirenEmbeddedLink(
                    class_=("record",),
                    rel=("item",),
                    href="https://api.example.com/records/42",
                    type="application/vnd.siren+json",
                    title="Architecture",
                ),
                SirenEmbeddedRepresentation(
                    class_=("record",),
                    rel=("item",),
                    title="Architecture",
                    properties={"id": "42"},
                    actions=(
                        SirenAction(
                            class_=("update",),
                            name="rename",
                            method="PATCH",
                            href="https://api.example.com/records/42",
                            title="Rename record",
                            type="application/json",
                            fields=(
                                SirenField(name="title", title="Title", value="Architecture"),
                                SirenField(
                                    name="visibility",
                                    type="radio",
                                    value=(
                                        SirenFieldValue(value="private", title="Private"),
                                        SirenFieldValue(value="public", title="Public", selected=True),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    links=(SirenLink(rel=("self",), href="https://api.example.com/records/42"),),
                ),
            ),
            actions=(
                SirenAction(
                    name="create",
                    method="POST",
                    href="https://api.example.com/records",
                ),
            ),
            links=(
                SirenLink(
                    class_=("collection",),
                    rel=("self",),
                    href="https://api.example.com/records",
                    type="application/vnd.siren+json",
                    title="Records",
                ),
            ),
        )

        assert document.model_dump(by_alias=True, mode="json", exclude_none=True) == {
            "class": ["collection"],
            "title": "Records",
            "properties": {"count": 1},
            "entities": [
                {
                    "class": ["record"],
                    "title": "Architecture",
                    "rel": ["item"],
                    "href": "https://api.example.com/records/42",
                    "type": "application/vnd.siren+json",
                },
                {
                    "class": ["record"],
                    "rel": ["item"],
                    "title": "Architecture",
                    "properties": {"id": "42"},
                    "actions": [
                        {
                            "class": ["update"],
                            "name": "rename",
                            "method": "PATCH",
                            "href": "https://api.example.com/records/42",
                            "title": "Rename record",
                            "type": "application/json",
                            "fields": [
                                {"name": "title", "type": "text", "title": "Title", "value": "Architecture"},
                                {
                                    "name": "visibility",
                                    "type": "radio",
                                    "value": [
                                        {"value": "private", "title": "Private", "selected": False},
                                        {"value": "public", "title": "Public", "selected": True},
                                    ],
                                },
                            ],
                        }
                    ],
                    "links": [{"rel": ["self"], "href": "https://api.example.com/records/42"}],
                },
            ],
            "actions": [{"name": "create", "method": "POST", "href": "https://api.example.com/records"}],
            "links": [
                {
                    "class": ["collection"],
                    "title": "Records",
                    "rel": ["self"],
                    "href": "https://api.example.com/records",
                    "type": "application/vnd.siren+json",
                }
            ],
        }
