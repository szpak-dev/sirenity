from django.urls import path
from ninja import Schema
from ninja_extra import NinjaExtraAPI, api_controller, http_get

from sirenity.api import SirenContinuation, SirenFollowUp, SirenScope, siren_follow_ups


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
        example_cursor: str = "example-cursor-1",
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
        example_locale: str = "example-en",
    ) -> ExampleExtraRecord:
        return ExampleExtraRecord(example_record_id=example_record_id, example_title=example_locale)


api = NinjaExtraAPI(urls_namespace="example_extra_continuations")
api.register_controllers(ExampleExtraJobController)
urlpatterns = [path("", api.urls)]
