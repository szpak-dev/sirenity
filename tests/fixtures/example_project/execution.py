from pydantic import JsonValue

from sirenity import SirenMcpExecution, SirenMcpOperation


class ExampleMcpExecutor:
    def execute(self, operation: SirenMcpOperation) -> SirenMcpExecution:
        if not isinstance(operation.body, dict):
            raise TypeError("update_example_resource requires an object body")
        result: dict[str, JsonValue] = {
            "example_resource_id": operation.path_values["example_resource_id"],
            "title": operation.body["title"],
            "metadata": operation.body["metadata"],
            "example_trace": operation.header_values["example_trace"],
        }
        if "example_page" in operation.query_values:
            result["example_page"] = operation.query_values["example_page"]
        if "example_session" in operation.cookie_values:
            result["example_session"] = operation.cookie_values["example_session"]
        return SirenMcpExecution(
            status=200,
            result=result,
            base_url="https://api.example.com",
        )
