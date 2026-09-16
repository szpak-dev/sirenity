from django.urls import path
from ninja import Schema
from ninja_extra import NinjaExtraAPI, api_controller, http_get

from sirenity.api import SirenContinuation


class ExampleExtraJobState(Schema):
    example_job_id: str
    example_state: str
    has_more: bool
    next_example_cursor: str


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


api = NinjaExtraAPI(urls_namespace="example_extra_continuations")
api.register_controllers(ExampleExtraJobController)
urlpatterns = [path("", api.urls)]
