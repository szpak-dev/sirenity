from ninja_extra import ControllerBase, api_controller, http_get, http_patch

from .rename_example_resource_payload import RenameExampleResourcePayload


@api_controller("/api/v1/example_resources")
class ExampleResourceController(ControllerBase):
    @http_get(
        operation_id="list_example_resources", summary="List example resources", description="List example resources."
    )
    def list_example_resources(self, page: int = 1) -> dict[str, list[dict[str, str]]]:
        return {"items": []}

    @http_get(
        "/{example_resource}",
        operation_id="get_example_resource",
        summary="Read example resource",
        description="Read an example resource.",
    )
    def get_example_resource(self, example_resource: str) -> dict[str, str]:
        return {"id": example_resource}

    @http_patch(
        "/{example_resource}",
        operation_id="rename_example_resource",
        summary="Rename example resource",
        description="Rename an example resource.",
    )
    def rename_example_resource(self, example_resource: str, payload: RenameExampleResourcePayload) -> dict[str, str]:
        return {"id": example_resource, "title": payload.title}
