import json
from importlib.resources import files

import pytest
from jsonschema import Draft4Validator, FormatChecker, ValidationError

import sirenity
from sirenity import (
    SirenAction,
    SirenDocument,
    SirenEmbeddedLink,
    SirenEmbeddedRepresentation,
    SirenField,
    SirenFieldValue,
    SirenityError,
    SirenLink,
)


class TestSchema:
    schema = json.loads(files(sirenity).joinpath("contexts/shared/siren_schema/values/siren.schema.json").read_text())
    validator = Draft4Validator(schema, format_checker=FormatChecker())

    @pytest.mark.parametrize(
        "payload",
        [
            {"links": [{"rel": ["self"], "href": "https://[invalid"}]},
            {"entities": [{"rel": []}]},
            {
                "actions": [
                    {
                        "name": "rename",
                        "href": "https://api.example.com/example_resources/42",
                        "fields": [{"name": "title", "type": "unsupported"}],
                    }
                ]
            },
        ],
    )
    def test_pinned_schema_rejects_invalid_public_payloads(self, payload):
        with pytest.raises(ValidationError):
            self.validator.validate(payload)

    @pytest.mark.parametrize(
        "value",
        (
            "https://api.example.com/%zz",
            "https://api.example.com/[]",
            "https://api.example.com/example_resources space",
        ),
    )
    def test_public_values_reject_uri_boundaries_rejected_by_the_pinned_schema(self, value):
        with pytest.raises(ValidationError):
            self.validator.validate({"links": [{"rel": ["self"], "href": value}]})
        with pytest.raises(SirenityError, match="Siren URI must be a valid URI"):
            SirenLink(rel=("self",), href=value)
        with pytest.raises(SirenityError, match="Siren relation must be an official relation token or URI"):
            SirenLink(rel=(value,), href="https://api.example.com/example_resources")

    def test_public_uri_values_accept_every_owner_supported_by_the_pinned_schema(self):
        document = SirenDocument(
            actions=(SirenAction(name="inspect", href="http://"),),
            entities=(SirenEmbeddedLink(rel=("self",), href="http://"),),
            links=(SirenLink(rel=("http://",), href="http://"),),
        )

        self.validator.validate(document.model_dump(by_alias=True, mode="json", exclude_none=True))

    @pytest.mark.parametrize("value", ("text", 1, 1.5))
    def test_public_field_scalar_values_match_the_pinned_schema(self, value):
        document = SirenDocument(
            actions=(
                SirenAction(
                    name="update",
                    href="https://api.example.com/example_resources",
                    fields=(SirenField(name="value", value=value),),
                ),
            ),
        )

        self.validator.validate(document.model_dump(by_alias=True, mode="json", exclude_none=True))

    @pytest.mark.parametrize("value", ("text", 1, 1.5))
    def test_public_field_value_objects_match_the_pinned_schema(self, value):
        document = SirenDocument(
            actions=(
                SirenAction(
                    name="update",
                    href="https://api.example.com/example_resources",
                    fields=(SirenField(name="value", value=(SirenFieldValue(value=value),)),),
                ),
            ),
        )

        self.validator.validate(document.model_dump(by_alias=True, mode="json", exclude_none=True))

    def test_public_field_values_reject_boolean_coercion(self):
        with pytest.raises(ValueError):
            SirenField(name="value", value=True)
        with pytest.raises(ValueError):
            SirenFieldValue(value=True)

    def test_public_models_reject_package_specific_action_field_members(self):
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            SirenField(name="title", required=True)

    def test_pinned_schema_identifies_the_upstream_draft_four_revision(self):
        assert self.schema["id"] == "http://sirenspec.org/schema#"
        assert self.schema["$schema"] == "http://json-schema.org/draft-04/schema#"
        assert "uri" in FormatChecker().checkers

    def test_public_root_fixture_conforms_to_the_pinned_schema(self):
        document = SirenDocument(
            class_=("api", "entry-point"),
            actions=(SirenAction(name="search", method="POST", href="https://api.example.com/search"),),
            links=(SirenLink(rel=("self",), href="https://api.example.com/"),),
        )

        self.validator.validate(document.model_dump(by_alias=True, mode="json", exclude_none=True))

    def test_public_collection_fixture_conforms_to_the_pinned_schema(self):
        document = SirenDocument(
            class_=("collection",),
            properties={"count": 1},
            entities=(
                SirenEmbeddedRepresentation(
                    class_=("example_resource",),
                    rel=("item",),
                    properties={"id": "42"},
                    links=(SirenLink(rel=("self",), href="https://api.example.com/example_resources/42"),),
                ),
            ),
            actions=(SirenAction(name="list", href="https://api.example.com/example_resources"),),
            links=(SirenLink(rel=("self",), href="https://api.example.com/example_resources"),),
        )

        self.validator.validate(document.model_dump(by_alias=True, mode="json", exclude_none=True))

    def test_public_entity_and_embedded_link_fixtures_conform_to_the_pinned_schema(self):
        document = SirenDocument(
            class_=("example_resource",),
            properties={"id": "42"},
            entities=(
                SirenEmbeddedLink(
                    rel=("collection",),
                    href="https://api.example.com/example_resources",
                ),
            ),
            actions=(
                SirenAction(
                    name="rename",
                    method="PATCH",
                    href="https://api.example.com/example_resources/42",
                    type="application/json",
                    fields=(SirenField(name="title", type="text"),),
                ),
            ),
            links=(SirenLink(rel=("self",), href="https://api.example.com/example_resources/42"),),
        )

        self.validator.validate(document.model_dump(by_alias=True, mode="json", exclude_none=True))
