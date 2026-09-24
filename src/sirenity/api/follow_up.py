"""Django follow-up integration.

<!-- docs:order=41 -->
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from pydantic import JsonValue

from ..contexts.shared import SirenScope
from .source_input import SirenSourceInput


class SirenOperationDecorator[**P, R](ABC):
    @abstractmethod
    def __call__(self, handler: Callable[P, R]) -> Callable[P, R]: ...


class SirenRouteDecorator[**P, R, S](ABC):
    @abstractmethod
    def __call__(
        self,
        path: str,
        *,
        response: Mapping[int, type[S]],
        operation_id: str,
        summary: str,
        description: str,
        openapi_extra: Mapping[str, JsonValue],
    ) -> SirenOperationDecorator[P, R]: ...


@dataclass(frozen=True)
class SirenFollowUp:
    """Declare one safe read target for :func:`siren_follow_ups`.

    ``parameters`` maps target path or query argument names to top-level response property names.
    Prefix an argument with ``path.`` or ``query.`` when its location is not otherwise unambiguous.
    ``rel`` and ``scope`` become the existing Siren relationship metadata on the generated OpenAPI
    Response Link Object. ``source_inputs`` maps target argument names to required source-request
    inputs; response-property parameters and source inputs must target distinct arguments.
    """

    operation_id: str
    parameters: Mapping[str, str]
    rel: str
    scope: SirenScope
    source_inputs: Mapping[str, SirenSourceInput] = field(default_factory=dict)


def siren_follow_ups[**P, R, S](
    route: SirenRouteDecorator[P, R, S],
    path: str,
    *,
    response: type[S],
    operation_id: str,
    follow_ups: Mapping[str, SirenFollowUp],
    summary: str,
    description: str,
    status: int,
) -> SirenOperationDecorator[P, R]:
    """Declare typed read follow-ups for a Django Ninja or Ninja Extra operation.

    Pass ``api.get`` for Django Ninja or ``http_get`` for Ninja Extra. Each mapping key becomes
    the OpenAPI response-link name, while its :class:`SirenFollowUp` supplies the target operation,
    response-property bindings, Siren relation, and target scope. Sirenity validates the generated
    links during normal startup compilation and exposes authorized safe reads as typed MCP
    invocations without parsing their rendered hrefs.
    Each follow-up may explicitly retain required, non-null source path, query, or body inputs while
    response-property bindings provide result-specific target arguments.

    ```python
    from sirenity import SirenFollowUp, SirenScope, siren_follow_ups

    @siren_follow_ups(
        api.get,
        "/api/dashboards/{dashboard_id}",
        response=Dashboard,
        operation_id="get_dashboard",
        follow_ups={
            "primary_record": SirenFollowUp(
                operation_id="get_record",
                parameters={"path.record_id": "primary_record_id"},
                rel="primary",
                scope=SirenScope.ENTITY,
            ),
        },
        status=200,
        summary="Read dashboard",
        description="Read one dashboard.",
    )
    def get_dashboard(request, dashboard_id: str) -> Dashboard:
        return Dashboard(dashboard_id=dashboard_id, primary_record_id="record-1")
    ```

    Optional target arguments omitted from ``parameters`` remain absent from the typed invocation,
    so defaults declared by the target operation continue to apply.
    """

    links = {
        name: {
            "operationId": follow_up.operation_id,
            "parameters": {
                argument: f"$response.body#/{property_name.replace('~', '~0').replace('/', '~1')}"
                for argument, property_name in follow_up.parameters.items()
            },
            "x-sirenity": {
                "rel": follow_up.rel,
                "scope": follow_up.scope.value,
                **(
                    {
                        "sourceInputs": {
                            target: (
                                "$request.body#/" + source.name.replace("~", "~0").replace("/", "~1")
                                if source.location == "body"
                                else f"$request.{source.location}.{source.name}"
                            )
                            for target, source in follow_up.source_inputs.items()
                        }
                    }
                    if follow_up.source_inputs
                    else {}
                ),
            },
        }
        for name, follow_up in follow_ups.items()
    }
    return route(
        path,
        response={status: response},
        operation_id=operation_id,
        summary=summary,
        description=description,
        openapi_extra={"responses": {status: {"links": links}}},
    )
