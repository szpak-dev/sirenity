from copy import deepcopy

import pytest
from django.conf import settings
from django.test import override_settings

from sirenity.api import SirenContractError, siren

from ..cases import DjangoCase

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])


class TestDjangoFollowUpAttacks(DjangoCase):
    def test_adversarial_unknown_target_is_rejected_from_the_generated_contract(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            contract = deepcopy(api.get_openapi_schema())
        link = contract["paths"]["/api/example_dashboards/{example_dashboard_id}"]["get"]["responses"][200]["links"][
            "primary_record"
        ]
        link["operationId"] = "get_missing_example_record"

        with pytest.raises(SirenContractError, match="references unknown operation"):
            siren(contract, source_path="/api", public_path="/siren")

    def test_invariant_invalid_target_binding_is_rejected_from_the_generated_contract(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            contract = deepcopy(api.get_openapi_schema())
        link = contract["paths"]["/api/example_dashboards/{example_dashboard_id}"]["get"]["responses"][200]["links"][
            "primary_record"
        ]
        link["parameters"] = {"path.example_missing_id": "$response.body#/primary_record_id"}

        with pytest.raises(SirenContractError, match="do not match the target route"):
            siren(contract, source_path="/api", public_path="/siren")


class TestDjangoFollowUpHappyPaths(DjangoCase):
    def test_ninja_declaration_generates_multiple_standard_response_links(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            contract = deepcopy(api.get_openapi_schema())
        operation = contract["paths"]["/api/example_dashboards/{example_dashboard_id}"]["get"]

        assert operation["responses"][200]["links"] == {
            "primary_record": {
                "operationId": "get_example_record",
                "parameters": {"path.example_record_id": "$response.body#/primary_record_id"},
                "x-sirenity": {
                    "rel": "item",
                    "scope": "entity",
                    "sourceInputs": {"query.example_locale": "$request.path.example_dashboard_id"},
                },
            },
            "secondary_record": {
                "operationId": "get_example_record",
                "parameters": {"path.example_record_id": "$response.body#/secondary_record_id"},
                "x-sirenity": {"rel": "alternate", "scope": "entity"},
            },
        }
        siren(contract, source_path="/api", public_path="/siren")

    def test_ninja_extra_declaration_generates_multiple_standard_response_links(self) -> None:
        from ..support.applications.django_ninja_extra import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja_extra"):
            contract = deepcopy(api.get_openapi_schema())
        operation = contract["paths"]["/api/example_extra_dashboards/{example_dashboard_id}"]["get"]

        assert operation["responses"][200]["links"] == {
            "primary_record": {
                "operationId": "get_example_extra_record",
                "parameters": {"path.example_record_id": "$response.body#/primary_record_id"},
                "x-sirenity": {
                    "rel": "item",
                    "scope": "entity",
                    "sourceInputs": {"query.example_locale": "$request.path.example_dashboard_id"},
                },
            },
            "secondary_record": {
                "operationId": "get_example_extra_record",
                "parameters": {"path.example_record_id": "$response.body#/secondary_record_id"},
                "x-sirenity": {"rel": "alternate", "scope": "entity"},
            },
        }
        siren(contract, source_path="/api", public_path="/siren")
