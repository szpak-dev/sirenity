from django.http import HttpRequest
from django.urls import path
from ninja import NinjaAPI, Schema

from sirenity.api import (
    SirenContinuation,
    SirenFollowUp,
    SirenScope,
    SirenSourceInput,
    siren_follow_ups,
    siren_pagination,
)


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


class ExampleDashboard(Schema):
    example_dashboard_id: str
    primary_record_id: str
    secondary_record_id: str


api = NinjaAPI(urls_namespace="example_continuations")


class ExampleHandlers:
    @staticmethod
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
        example_cursor: str,
        example_filter: str,
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
    
    
    @staticmethod
    @siren_pagination(
        api.get,
        "/api/example_records",
        response=ExampleRecordPage,
        operation_id="list_example_records",
        continuation={"example_offset": "next_example_offset", "example_limit": "example_limit"},
        source_inputs={
            "query.example_filter": SirenSourceInput(
                location="query",
                name="example_filter",
            )
        },
        summary="List example records",
        description="List one page of example records.",
    )
    def list_example_records(
        request: HttpRequest,
        example_filter: str,
        example_offset: int,
        example_limit: int,
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
    
    
    @staticmethod
    @siren_follow_ups(
        api.get,
        "/api/example_dashboards/{example_dashboard_id}",
        response=ExampleDashboard,
        operation_id="get_example_dashboard",
        follow_ups={
            "primary_record": SirenFollowUp(
                operation_id="get_example_record",
                parameters={"path.example_record_id": "primary_record_id"},
                rel="item",
                scope=SirenScope.ENTITY,
                source_inputs={
                    "query.example_locale": SirenSourceInput(
                        location="path",
                        name="example_dashboard_id",
                    )
                },
            ),
            "secondary_record": SirenFollowUp(
                operation_id="get_example_record",
                parameters={"path.example_record_id": "secondary_record_id"},
                rel="alternate",
                scope=SirenScope.ENTITY,
            ),
        },
        summary="Read example dashboard",
        description="Read one example dashboard.",
    )
    def get_example_dashboard(request: HttpRequest, example_dashboard_id: str) -> ExampleDashboard:
        return ExampleDashboard(
            example_dashboard_id=example_dashboard_id,
            primary_record_id="example-record-1",
            secondary_record_id="example-record-2",
        )
    
    
    @staticmethod
    @api.get(
        "/api/example_records/{example_record_id}",
        response=ExampleRecord,
        operation_id="get_example_record",
        summary="Read example record",
        description="Read one example record.",
    )
    def get_example_record(
        request: HttpRequest,
        example_record_id: str,
        example_locale: str,
    ) -> ExampleRecord:
        return ExampleRecord(example_record_id=example_record_id, example_title=example_locale)
    
    
urlpatterns = [path("", api.urls)]
