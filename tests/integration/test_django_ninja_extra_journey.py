from copy import deepcopy

import pytest
from django.conf import settings
from django.test import override_settings

from sirenity.api import SirenAdapterRequest, SirenContractError, siren_adapter

from ..cases import DjangoCase

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])


class TestDjangoNinjaExtraJourneyAttacks(DjangoCase):
    def test_adversarial_decorator_contract_rejects_a_missing_target_query(self) -> None:
        from ..support.applications.django_ninja_extra import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja_extra"):
            contract = deepcopy(api.get_openapi_schema())
        operation = contract["paths"]["/api/example_extra_jobs/{example_job_id}"]["get"]
        operation["parameters"] = [
            parameter for parameter in operation["parameters"] if parameter["name"] != "example_cursor"
        ]

        with pytest.raises(SirenContractError, match="does not match the target operation"):
            siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())


class TestDjangoNinjaExtraJourneyHappyPaths(DjangoCase):
    def test_decorator_contract_projects_a_typed_bounded_continuation(self) -> None:
        from ..support.applications.django_ninja_extra import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja_extra"):
            contract = api.get_openapi_schema()
        adapter = siren_adapter(contract, source_path="/api", public_path="/siren", profiles=())

        response = adapter.respond(
            SirenAdapterRequest(
                operation_id="get_example_extra_job",
                status=200,
                result={
                    "example_job_id": "example-job-1",
                    "example_state": "running",
                    "has_more": True,
                    "next_example_cursor": "example-cursor-2",
                },
                base_url="https://api.example.test",
                path_values={"example_job_id": "example-job-1"},
            )
        )

        assert response.payload["links"][-1]["rel"] == ["next"]
        assert response.continuations[0].operation_id == "get_example_extra_job"
        assert response.continuations[0].arguments == {
            "example_job_id": "example-job-1",
            "example_cursor": "example-cursor-2",
        }
