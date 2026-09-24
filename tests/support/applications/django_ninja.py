from typing import Annotated

from django.http import HttpRequest
from django.urls import path
from ninja import NinjaAPI, Query, Schema

from sirenity.api import (
    SirenContinuation,
    SirenFollowUp,
    SirenItemFollowUp,
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


class ExampleItemManifest(Schema):
    item_id: str
    expected_revision: str


class ExampleItemPage(Schema):
    items: list[ExampleItemManifest]
    has_more: bool
    next_offset: int
    limit: int


class ExampleItemContent(Schema):
    item_id: str
    expected_revision: str
    content: str


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
        example_cursor: Annotated[str, Query("example-cursor-1")],
        example_filter: Annotated[str, Query("example-open")],
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
        item_follow_ups={},
        status=200,
    )
    def list_example_records(
        request: HttpRequest,
        example_filter: str,
        example_offset: Annotated[int, Query(0)],
        example_limit: Annotated[int, Query(2)],
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
    @siren_pagination(
        api.get,
        "/api/example_items",
        response=ExampleItemPage,
        operation_id="list_example_items",
        continuation={"offset": "next_offset", "limit": "limit"},
        item_follow_ups={
            "content": SirenItemFollowUp(
                operation_id="read_example_item_content",
                parameters={"path.item_id": "item_id", "query.expected_revision": "expected_revision"},
                rel="item",
                scope=SirenScope.ENTITY,
                item_collection="items",
            )
        },
        summary="List example items",
        description="List one page of example item manifests.",
        source_inputs={},
        status=200,
    )
    def list_example_items(
        request: HttpRequest,
        offset: Annotated[int, Query(0)],
        limit: Annotated[int, Query(2)],
    ) -> ExampleItemPage:
        return ExampleItemPage(
            items=([ExampleItemManifest(item_id="item-1", expected_revision="revision-1")] if offset == 0 else []),
            has_more=offset == 0,
            next_offset=2,
            limit=limit,
        )

    @staticmethod
    @api.get(
        "/api/example_items/{item_id}",
        response=ExampleItemContent,
        operation_id="read_example_item_content",
        summary="Read example item content",
        description="Read one example item's content.",
    )
    def read_example_item_content(
        request: HttpRequest,
        item_id: str,
        expected_revision: str,
    ) -> ExampleItemContent:
        return ExampleItemContent(
            item_id=item_id,
            expected_revision=expected_revision,
            content="example content",
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
        status=200,
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
        example_locale: Annotated[str, Query("example-en")],
    ) -> ExampleRecord:
        return ExampleRecord(example_record_id=example_record_id, example_title=example_locale)


urlpatterns = [path("", api.urls)]
