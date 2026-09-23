from urllib.parse import urlsplit

from django.conf import settings
from django.test import Client, override_settings

from sirenity.api import siren_configuration

from ..cases import DjangoCase

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])


class TestDjangoJourneyAttacks(DjangoCase):
    def test_adversarial_non_siren_request_preserves_the_application_response(self) -> None:
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
            response = Client(HTTP_ACCEPT="application/json").get("/api/example_jobs/example-job-1")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/json")
        assert response.json()["example_state"] == "running"

    def test_recovery_json_request_succeeds_after_siren_continuation_flow(self) -> None:
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
            siren_response = Client(HTTP_ACCEPT="application/vnd.siren+json").get("/siren/example_jobs/example-job-1")
            json_response = Client(HTTP_ACCEPT="application/json").get("/api/example_jobs/example-job-1")

        assert siren_response.status_code == 200
        assert json_response.status_code == 200
        assert json_response.json()["example_job_id"] == "example-job-1"


class TestDjangoJourneyHappyPaths(DjangoCase):
    def test_prebuilt_configuration_retains_its_caller_owned_lifecycle(self) -> None:
        configuration = siren_configuration(
            openapi="tests.support.applications.configuration.EXAMPLE_BOUNDED_OPENAPI",
            source_path="/api",
            public_path="/siren",
            policy="tests.support.collaborators.ExamplePolicy",
        )

        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF="tests.support.applications.django_ninja",
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY=configuration,
        ):
            response = Client(HTTP_ACCEPT="application/vnd.siren+json").get("/siren/example_jobs/example-job-1")

        assert response.status_code == 200
        assert configuration.adapter().match("GET", "/siren/example_jobs/example-job-1") is not None

    def test_ninja_middleware_and_bounded_continuation_form_one_http_flow(self) -> None:
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
            first = client.get("/siren/example_jobs/example-job-1")
            target = urlsplit(first.json()["links"][-1]["href"])
            final = client.get(f"{target.path}?{target.query}")

        assert first.status_code == 200
        assert first["Content-Type"].startswith("application/vnd.siren+json")
        assert first.json()["links"][-1]["rel"] == ["next"]
        assert final.json()["properties"]["example_state"] == "complete"
        assert [link["rel"] for link in final.json()["links"]] == [["self"]]

    def test_ninja_middleware_and_pagination_form_one_http_flow(self) -> None:
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
            first = client.get("/siren/example_records?example_filter=example-open&example_offset=0&example_limit=2")
            target = urlsplit(first.json()["links"][-1]["href"])
            final = client.get(f"{target.path}?{target.query}")

        assert first.json()["entities"][0]["properties"]["example_record_id"] == ("example-record-1")
        assert final.status_code == 200
        assert "entities" not in final.json()
        assert [link["rel"] for link in final.json()["links"]] == [["self"]]
