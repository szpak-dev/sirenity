from django.http import HttpRequest
from django.urls import path
from ninja import NinjaAPI, Schema

from sirenity.api import SirenContinuation, siren_pagination


class ExampleJobState(Schema):
    example_job_id: str
    example_state: str
    has_more: bool
    next_example_cursor: str


class ExampleRecord(Schema):
    example_record_id: str
    example_title: str


class ExampleRecordPage(Schema):
    example_items: list[ExampleRecord]
    has_more: bool
    next_example_offset: int
    example_limit: int


api = NinjaAPI(urls_namespace="example_continuations")


@SirenContinuation(
    api.get,
    "/api/example_jobs/{example_job_id}",
    response=ExampleJobState,
    operation_id="get_example_job",
    continuation={"example_cursor": "next_example_cursor"},
    summary="Read example job",
    description="Read the current state of one example job.",
)
def get_example_job(
    request: HttpRequest,
    example_job_id: str,
    example_cursor: str = "example-cursor-1",
    example_filter: str = "example-open",
) -> ExampleJobState:
    if example_cursor == "example-cursor-2":
        return ExampleJobState(
            example_job_id=example_job_id,
            example_state="complete",
            has_more=False,
            next_example_cursor="example-cursor-2",
        )
    return ExampleJobState(
        example_job_id=example_job_id,
        example_state="running",
        has_more=True,
        next_example_cursor="example-cursor-2",
    )


@siren_pagination(
    api.get,
    "/api/example_records",
    response=ExampleRecordPage,
    operation_id="list_example_records",
    continuation={"example_offset": "next_example_offset", "example_limit": "example_limit"},
    summary="List example records",
    description="List one page of example records.",
)
def list_example_records(
    request: HttpRequest,
    example_offset: int = 0,
    example_limit: int = 2,
) -> ExampleRecordPage:
    return ExampleRecordPage(
        example_items=(
            [ExampleRecord(example_record_id="example-record-1", example_title="Example first")]
            if example_offset == 0
            else []
        ),
        has_more=example_offset == 0,
        next_example_offset=2,
        example_limit=example_limit,
    )


urlpatterns = [path("", api.urls)]
