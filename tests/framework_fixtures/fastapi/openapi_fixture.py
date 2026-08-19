from typing import Any

from fastapi import FastAPI

from .widget_controller import WidgetController


class FastApiOpenApiFixture:
    def __init__(self) -> None:
        self.application = FastAPI(title="Framework fixture", version="1")
        self.controller = WidgetController()
        self.application.add_api_route(
            "/api/v1/widgets",
            self.controller.list_widgets,
            methods=["GET"],
            operation_id="list_widgets",
            summary="List widgets",
            description="List widgets.",
        )
        self.application.add_api_route(
            "/api/v1/widgets/{widget}",
            self.controller.get_widget,
            methods=["GET"],
            operation_id="get_widget",
            summary="Read widget",
            description="Read a widget.",
        )
        self.application.add_api_route(
            "/api/v1/widgets/{widget}",
            self.controller.rename_widget,
            methods=["PATCH"],
            operation_id="rename_widget",
            summary="Rename widget",
            description="Rename a widget.",
        )

    def document(self) -> dict[str, Any]:
        return self.application.openapi()
