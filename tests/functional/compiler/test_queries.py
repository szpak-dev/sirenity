import pytest

from sirenity import SirenContext, SirenityError, siren

from .openapi_documents import ROUTE_POLICY_SCHEMA, SCHEMA


class TestQueries:
    def test_public_facade_rejects_nonscalar_query_values_and_recovers(self):
        with pytest.raises(SirenityError, match="Siren query values must be scalar"):
            SirenContext(base_url="https://api.example.com", scope="root", query=(("tag", ["one", "two"]),))

        with pytest.raises(SirenityError, match="Siren projection failed"):
            siren(ROUTE_POLICY_SCHEMA).project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="collection",
                    resource="example_resource",
                    query=(("page", 2),),
                )
            )

        payload = (
            siren(SCHEMA)
            .project(
                SirenContext(
                    base_url="https://api.example.com",
                    scope="collection",
                    resource="example_resource",
                    query=(("page", 2),),
                )
            )
            .model_dump(by_alias=True, mode="json", exclude_none=True)
        )
        assert payload["links"] == [{"rel": ["self"], "href": "https://api.example.com/example_resources?page=2"}]

    def test_public_facade_serializes_ordered_repeated_and_escaped_query_values(self):
        document = siren(SCHEMA).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                query=(
                    ("filter", "a/b & c"),
                    ("tag", "first"),
                    ("tag", "second"),
                    ("empty", ""),
                    ("missing", None),
                    ("ż", "✓"),
                ),
                capabilities=frozenset({"list_example_resources"}),
            )
        )
        payload = document.model_dump(by_alias=True, mode="json", exclude_none=True)

        href = "https://api.example.com/example_resources?filter=a%2Fb%20%26%20c&tag=first&tag=second&empty=&missing=&%C5%BC=%E2%9C%93"
        assert payload["links"] == [{"rel": ["self"], "href": href}]
        assert payload["actions"] == [
            {"name": "list_example_resources", "href": href, "method": "GET", "title": "List example resources"}
        ]

    def test_public_facade_limits_root_query_values_to_the_self_link(self):
        document = siren(SCHEMA).project(
            SirenContext(base_url="https://api.example.com", scope="root", query=(("format", "siren"),))
        )
        payload = document.model_dump(by_alias=True, mode="json", exclude_none=True)

        assert payload["links"] == [
            {"title": "Sirenity", "rel": ["self"], "href": "https://api.example.com/?format=siren"},
            {"rel": ["collection"], "href": "https://api.example.com/example_resources"},
        ]
