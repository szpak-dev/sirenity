from urllib.parse import urlsplit

import pytest
from django.conf import settings
from django.test import Client, override_settings

from sirenity.api import SirenContractError, siren

from ..cases import DjangoCase

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])


class TestDjangoContinuationAttacks(DjangoCase):
    def test_adversarial_generated_contract_is_rejected_when_bounded_query_is_missing(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            contract = api.get_openapi_schema()
        operation = contract["paths"]["/api/example_jobs/{example_job_id}"]["get"]
        operation["parameters"] = [
            parameter for parameter in operation["parameters"] if parameter["name"] != "example_cursor"
        ]

        with pytest.raises(SirenContractError, match="does not match the target operation"):
            siren(contract, source_path="/api", public_path="/siren")

    def test_invariant_plain_json_request_is_not_replaced(self) -> None:
        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            response = Client().get("/api/example_jobs/example-job-1")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/json")
        assert response.json()["example_state"] == "running"

    def test_cleanup_a_final_page_contains_no_stale_next_link(self) -> None:
        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF="tests.support.applications.django_ninja",
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY={
                "OPENAPI": "tests.support.applications.django_ninja.api",
                "SOURCE_PATH": "/api",
                "PUBLIC_PATH": "/siren",
                "POLICY": "tests.support.collaborators.ExamplePolicy",
            },
        ):
            response = Client(HTTP_ACCEPT="application/vnd.siren+json").get(
                "/siren/example_jobs/example-job-1?example_cursor=example-cursor-2"
            )

        assert [link["rel"] for link in response.json()["links"]] == [["self"]]

    def test_recovery_plain_json_remains_available_after_a_siren_request(self) -> None:
        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF="tests.support.applications.django_ninja",
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY={
                "OPENAPI": "tests.support.applications.django_ninja.api",
                "SOURCE_PATH": "/api",
                "PUBLIC_PATH": "/siren",
                "POLICY": "tests.support.collaborators.ExamplePolicy",
            },
        ):
            client = Client(HTTP_ACCEPT="application/vnd.siren+json")
            assert client.get("/siren/example_jobs/example-job-1").status_code == 200
            recovered = Client().get("/api/example_jobs/example-job-1")

        assert recovered.status_code == 200
        assert recovered.json()["example_job_id"] == "example-job-1"


class TestDjangoContinuationHappyPaths(DjangoCase):
    def test_bounded_declaration_generates_one_standard_typed_link(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            operation = api.get_openapi_schema()["paths"]["/api/example_jobs/{example_job_id}"]["get"]

        assert operation["summary"] == "Read example job"
        assert operation["description"] == "Read the current state of one example job."
        assert operation["responses"][200]["links"] == {
            "next": {
                "operationId": "get_example_job",
                "parameters": {
                    "example_cursor": "$response.body#/next_example_cursor",
                },
                "x-sirenity": {"continuation": "bounded"},
            }
        }

    def test_pagination_declaration_generates_one_standard_link(self) -> None:
        from ..support.applications.django_ninja import api

        with override_settings(ROOT_URLCONF="tests.support.applications.django_ninja"):
            operation = api.get_openapi_schema()["paths"]["/api/example_records"]["get"]

        assert operation["responses"][200]["links"] == {
            "next": {
                "operationId": "list_example_records",
                "parameters": {
                    "example_offset": "$response.body#/next_example_offset",
                    "example_limit": "$response.body#/example_limit",
                },
            }
        }

    def test_bounded_endpoint_exposes_and_follows_the_next_public_request(self) -> None:
        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF="tests.support.applications.django_ninja",
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY={
                "OPENAPI": "tests.support.applications.django_ninja.api",
                "SOURCE_PATH": "/api",
                "PUBLIC_PATH": "/siren",
                "POLICY": "tests.support.collaborators.ExamplePolicy",
            },
        ):
            client = Client(HTTP_ACCEPT="application/vnd.siren+json")
            first = client.get(
                "/siren/example_jobs/example-job-1?example_filter=example-open&example_cursor=example-cursor-1"
            )
            next_request = urlsplit(first.json()["links"][-1]["href"])
            second = client.get(f"{next_request.path}?{next_request.query}")

        assert first.status_code == 200
        assert first.json()["links"][-1]["rel"] == ["next"]
        assert second.status_code == 200
        assert second.json()["properties"]["example_state"] == "complete"
        assert [link["rel"] for link in second.json()["links"]] == [["self"]]

    def test_paginated_endpoint_exposes_and_follows_the_next_public_request(self) -> None:
        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF="tests.support.applications.django_ninja",
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY={
                "OPENAPI": "tests.support.applications.django_ninja.api",
                "SOURCE_PATH": "/api",
                "PUBLIC_PATH": "/siren",
                "POLICY": "tests.support.collaborators.ExamplePolicy",
            },
        ):
            client = Client(HTTP_ACCEPT="application/vnd.siren+json")
            first = client.get("/siren/example_records?example_offset=0&example_limit=2")
            next_request = urlsplit(first.json()["links"][-1]["href"])
            second = client.get(f"{next_request.path}?{next_request.query}")

        assert first.json()["links"][-1]["rel"] == ["next"]
        assert second.status_code == 200
        assert "entities" not in second.json()
        assert [link["rel"] for link in second.json()["links"]] == [["self"]]
