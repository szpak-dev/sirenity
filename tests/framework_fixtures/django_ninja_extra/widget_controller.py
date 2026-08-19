from ninja_extra import ControllerBase, api_controller, http_get, http_patch

from .rename_widget_payload import RenameWidgetPayload


@api_controller("/api/v1/widgets")
class WidgetController(ControllerBase):
    @http_get(operation_id="list_widgets", summary="List widgets", description="List widgets.")
    def list_widgets(self, page: int = 1) -> dict[str, list[dict[str, str]]]:
        return {"items": []}

    @http_get("/{widget}", operation_id="get_widget", summary="Read widget", description="Read a widget.")
    def get_widget(self, widget: str) -> dict[str, str]:
        return {"id": widget}

    @http_patch("/{widget}", operation_id="rename_widget", summary="Rename widget", description="Rename a widget.")
    def rename_widget(self, widget: str, payload: RenameWidgetPayload) -> dict[str, str]:
        return {"id": widget, "title": payload.title}
