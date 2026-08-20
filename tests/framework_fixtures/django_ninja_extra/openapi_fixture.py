from typing import Any

from ninja_extra import NinjaExtraAPI

from .example_resource_controller import ExampleResourceController


class DjangoNinjaExtraOpenApiFixture:
    def __init__(self) -> None:
        self.application = NinjaExtraAPI(title="Framework fixture", version="1")
        self.application.register_controllers(ExampleResourceController)

    def document(self) -> dict[str, Any]:
        return self.application.get_openapi_schema(path_prefix="")
