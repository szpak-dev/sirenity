from typing import Annotated

from django.urls import path
from ninja import Query, Schema
from ninja_extra import NinjaExtraAPI, api_controller, http_get

from sirenity.api import (
    SirenContinuation,
    SirenFollowUp,
    SirenItemFollowUp,
    SirenScope,
    SirenSourceInput,
    siren_follow_ups,
    siren_pagination,
)


class ExampleExtraJobState(Schema):
    example_job_id: str
    example_state: str
    has_more: bool
    next_example_cursor: str


class ExampleExtraDashboard(Schema):
    example_dashboard_id: str
    primary_record_id: str
    secondary_record_id: str


class ExampleExtraRecord(Schema):
    example_record_id: str
    example_title: str


class ExampleExtraItemManifest(Schema):
    item_id: str
    expected_revision: str


class ExampleExtraItemPage(Schema):
    items: list[ExampleExtraItemManifest]
    has_more: bool
    next_offset: int
    limit: int


class ExampleExtraItemContent(Schema):
    item_id: str
    expected_revision: str
    content: str


@api_controller("")
class ExampleExtraJobController:
    @SirenContinuation(
        http_get,
        "/api/example_extra_jobs/{example_job_id}",
        response=ExampleExtraJobState,
        operation_id="get_example_extra_job",
        continuation={"example_cursor": "next_example_cursor"},
        summary="Read example extra job",
        description="Read the current state of one example Ninja Extra job.",
    )
    def get_example_job(
        self,
        example_job_id: str,
        example_cursor: Annotated[str, Query("example-cursor-1")],
    ) -> ExampleExtraJobState:
        if example_cursor == "example-cursor-2":
            return ExampleExtraJobState(
                example_job_id=example_job_id,
                example_state="complete",
                has_more=False,
                next_example_cursor="example-cursor-2",
            )
        return ExampleExtraJobState(
            example_job_id=example_job_id,
            example_state="running",
            has_more=True,
            next_example_cursor="example-cursor-2",
        )

    @siren_pagination(
        http_get,
        "/api/example_items",
        response=ExampleExtraItemPage,
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
        self,
        offset: Annotated[int, Query(0)],
        limit: Annotated[int, Query(2)],
    ) -> ExampleExtraItemPage:
        return ExampleExtraItemPage(
            items=([ExampleExtraItemManifest(item_id="item-1", expected_revision="revision-1")] if offset == 0 else []),
            has_more=offset == 0,
            next_offset=2,
            limit=limit,
        )

    @http_get(
        "/api/example_items/{item_id}",
        response=ExampleExtraItemContent,
        operation_id="read_example_item_content",
        summary="Read example item content",
        description="Read one example item's content.",
    )
    def read_example_item_content(
        self,
        item_id: str,
        expected_revision: str,
    ) -> ExampleExtraItemContent:
        return ExampleExtraItemContent(
            item_id=item_id,
            expected_revision=expected_revision,
            content="example content",
        )

    @siren_follow_ups(
        http_get,
        "/api/example_extra_dashboards/{example_dashboard_id}",
        response=ExampleExtraDashboard,
        operation_id="get_example_extra_dashboard",
        follow_ups={
            "primary_record": SirenFollowUp(
                operation_id="get_example_extra_record",
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
                operation_id="get_example_extra_record",
                parameters={"path.example_record_id": "secondary_record_id"},
                rel="alternate",
                scope=SirenScope.ENTITY,
            ),
        },
        summary="Read example extra dashboard",
        description="Read one example Ninja Extra dashboard.",
        status=200,
    )
    def get_example_dashboard(self, example_dashboard_id: str) -> ExampleExtraDashboard:
        return ExampleExtraDashboard(
            example_dashboard_id=example_dashboard_id,
            primary_record_id="example-record-1",
            secondary_record_id="example-record-2",
        )

    @http_get(
        "/api/example_extra_records/{example_record_id}",
        response=ExampleExtraRecord,
        operation_id="get_example_extra_record",
        summary="Read example extra record",
        description="Read one example Ninja Extra record.",
    )
    def get_example_record(
        self,
        example_record_id: str,
        example_locale: Annotated[str, Query("example-en")],
    ) -> ExampleExtraRecord:
        return ExampleExtraRecord(example_record_id=example_record_id, example_title=example_locale)


api = NinjaExtraAPI(urls_namespace="example_extra_continuations")
api.register_controllers(ExampleExtraJobController)
urlpatterns = [path("", api.urls)]
