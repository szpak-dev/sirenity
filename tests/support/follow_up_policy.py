from pydantic import JsonValue

from sirenity.api import SirenAdapterPolicy


class ExampleFollowUpPolicy:
    def select(
        self,
        operation_id: str | None,
        status: int,
        request: object,
        result: JsonValue,
    ) -> SirenAdapterPolicy:
        return SirenAdapterPolicy(
            capabilities=frozenset(
                {
                    "get_example_dashboard",
                    "get_example_record",
                }
            )
        )


class ExampleDashboardOnlyPolicy:
    def select(
        self,
        operation_id: str | None,
        status: int,
        request: object,
        result: JsonValue,
    ) -> SirenAdapterPolicy:
        return SirenAdapterPolicy(capabilities=frozenset({"get_example_dashboard"}))
