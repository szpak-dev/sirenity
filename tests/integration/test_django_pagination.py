import pytest
from django.conf import settings
from django.test import Client, override_settings

from sirenity import SirenityError

if not settings.configured:
    settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])

SIREN_MEDIA_TYPE = "application/vnd.siren+json"
FRAMEWORKS = (
    "tests.framework_fixtures.django_pagination_ninja",
    "tests.framework_fixtures.django_pagination_ninja_extra",
)


def assert_application_rejects(openapi: str, source_path: str, message: str) -> None:
    with (
        override_settings(
            ALLOWED_HOSTS=["testserver"],
            ROOT_URLCONF="tests.framework_fixtures.django_pagination_invalid",
            MIDDLEWARE=["sirenity.SirenMiddleware"],
            SIRENITY={"OPENAPI": openapi, "SOURCE_PATH": source_path, "PUBLIC_PATH": "/siren"},
        ),
        pytest.raises(SirenityError, match=message),
    ):
        Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).get("/siren/articles")


def test_application_rejects_a_continuation_query_absent_from_the_operation() -> None:
    assert_application_rejects(
        "tests.framework_fixtures.django_pagination_invalid.missing_query_api",
        "/missing-query/api",
        "response link parameter does not match the target operation",
    )


def test_application_rejects_a_continuation_value_absent_from_the_response() -> None:
    assert_application_rejects(
        "tests.framework_fixtures.django_pagination_invalid.missing_response_api",
        "/missing-response/api",
        "continuation properties must exist and be required",
    )


def test_application_rejects_integer_and_string_versions_of_the_same_status() -> None:
    assert_application_rejects(
        "tests.framework_fixtures.django_pagination_invalid.duplicate_status_api",
        "/duplicate-status/api",
        "duplicate response status: 200",
    )


@pytest.mark.parametrize("application", FRAMEWORKS)
def test_application_exposes_one_standard_next_link_in_generated_openapi(application: str) -> None:
    with override_settings(ROOT_URLCONF=application):
        response = Client().get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/articles"]["get"]
    assert list(operation["responses"]) == ["200"]
    assert operation["responses"]["200"]["links"] == {
        "next": {
            "operationId": operation["operationId"],
            "parameters": {
                "offset": "$response.body#/next_offset",
                "limit": "$response.body#/limit",
            },
        }
    }


def get_page(offset: int) -> dict:
    application = "tests.framework_fixtures.django_pagination_ninja"
    with override_settings(
        ALLOWED_HOSTS=["testserver"],
        ROOT_URLCONF=application,
        MIDDLEWARE=["sirenity.SirenMiddleware"],
        SIRENITY={
            "OPENAPI": f"{application}.api",
            "SOURCE_PATH": "/api",
            "PUBLIC_PATH": "/siren",
        },
    ):
        response = Client(HTTP_ACCEPT=SIREN_MEDIA_TYPE).get(f"/siren/articles?offset={offset}&limit=2")

    assert response.status_code == 200
    return response.json()


def test_incomplete_page_exposes_the_next_application_request() -> None:
    page = get_page(0)

    assert page["links"][-1] == {
        "rel": ["next"],
        "title": "Next page",
        "href": "http://testserver/siren/articles?offset=2&limit=2",
    }


def test_final_page_omits_the_next_application_request() -> None:
    page = get_page(2)

    assert [link["rel"] for link in page["links"]] == [["self"]]
