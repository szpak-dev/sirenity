# Django follow-up integration

## `SirenFollowUp`

Declare one safe read target for :func:`siren_follow_ups`.

``parameters`` maps target path or query argument names to top-level response property names.
Prefix an argument with ``path.`` or ``query.`` when its location is not otherwise unambiguous.
``rel`` and ``scope`` become the existing Siren relationship metadata on the generated OpenAPI
Response Link Object. ``source_inputs`` maps target argument names to required source-request
inputs; response-property parameters and source inputs must target distinct arguments.

## `siren_follow_ups`

Declare typed read follow-ups for a Django Ninja or Ninja Extra operation.

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
