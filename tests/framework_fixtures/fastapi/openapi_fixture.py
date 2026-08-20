from typing import Any

from fastapi import FastAPI

from .example_resource_controller import ExampleResourceController


class FastApiOpenApiFixture:
    def __init__(self) -> None:
        self.application = FastAPI(title="Framework fixture", version="1")
        self.controller = ExampleResourceController()
        self.application.add_api_route(
            "/api/v1/example_resources",
            self.controller.list_example_resources,
            methods=["GET"],
            operation_id="list_example_resources",
            summary="List example resources",
            description="List example resources.",
        )
        self.application.add_api_route(
            "/api/v1/example_resources/{example_resource}",
            self.controller.get_example_resource,
            methods=["GET"],
            operation_id="get_example_resource",
            summary="Read example resource",
            description="Read an example resource.",
        )
        self.application.add_api_route(
            "/api/v1/example_resources/{example_resource}",
            self.controller.rename_example_resource,
            methods=["PATCH"],
            operation_id="rename_example_resource",
            summary="Rename example resource",
            description="Rename an example resource.",
        )

    def document(self) -> dict[str, Any]:
        return self.application.openapi()
