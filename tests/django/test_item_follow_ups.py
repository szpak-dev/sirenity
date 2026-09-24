from copy import deepcopy

import pytest
from django.conf import settings
from django.test import override_settings

from sirenity.api import SirenContractError, siren

from ..cases import DjangoCase

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])


class TestDjangoItemFollowUpAttacks(DjangoCase):
    def test_optional_item_property_is_rejected_during_compilation(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            contract = deepcopy(api.get_openapi_schema())
        schema = contract["components"]["schemas"]["ExampleItemManifest"]
        schema["required"].remove("item_id")

        with pytest.raises(SirenContractError, match="properties must exist and be required"):
            siren(contract, source_path="/api", public_path="/siren")


class TestDjangoItemFollowUpHappyPaths(DjangoCase):
    def test_ninja_declaration_generates_an_item_scoped_response_link(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            operation = api.get_openapi_schema()["paths"]["/api/example_items"]["get"]

        assert operation["responses"][200]["links"]["content"] == {
            "operationId": "read_example_item_content",
            "parameters": {
                "path.item_id": "$response.body#/item_id",
                "query.expected_revision": "$response.body#/expected_revision",
            },
            "x-sirenity": {
                "rel": "item",
                "scope": "entity",
                "itemCollection": "$response.body#/items",
            },
        }

    def test_ninja_extra_declaration_generates_an_item_scoped_response_link(self) -> None:
        from ..support.applications.django_ninja_extra import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja_extra"):
            operation = api.get_openapi_schema()["paths"]["/api/example_items"]["get"]

        assert operation["responses"][200]["links"]["content"] == {
            "operationId": "read_example_item_content",
            "parameters": {
                "path.item_id": "$response.body#/item_id",
                "query.expected_revision": "$response.body#/expected_revision",
            },
            "x-sirenity": {
                "rel": "item",
                "scope": "entity",
                "itemCollection": "$response.body#/items",
            },
        }
