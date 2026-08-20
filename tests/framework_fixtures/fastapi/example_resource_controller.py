from .rename_example_resource_payload import RenameExampleResourcePayload


class ExampleResourceController:
    def list_example_resources(self, page: int = 1) -> dict[str, list[dict[str, str]]]:
        return {"items": []}

    def get_example_resource(self, example_resource: str) -> dict[str, str]:
        return {"id": example_resource}

    def rename_example_resource(self, example_resource: str, payload: RenameExampleResourcePayload) -> dict[str, str]:
        return {"id": example_resource, "title": payload.title}
