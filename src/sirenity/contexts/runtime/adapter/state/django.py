import json
from collections.abc import Callable

from sirenity.contexts.shared import BaseState, SirenityError

from ..contracts import SirenCapabilityPolicy
from ..values import SirenAccept, SirenAdapterPolicy, SirenAdapterRequest
from .adapter import SirenAdapter


class SirenDjangoMiddleware(BaseState):
    """Render negotiated Django Ninja/Ninja Extra JSON responses as Siren.

    Configure this callable as Django middleware. The standard loader supplies
    `SirenAllowAllPolicy` when no application authorization policy is configured; direct callers
    provide a `SirenCapabilityPolicy` or a callable returning `SirenAdapterPolicy`.
    It calls the wrapped operation exactly once and transforms only matched JSON-compatible or
    content-free responses. Unmatched, non-JSON, streaming, redirect, 304, and already-Siren responses
    pass through without projection, as do all requests that do not select Siren. Negotiation honors
    quality, specificity, wildcards, and case-insensitive media types; missing or wildcard-only Accept
    values retain JSON because neither explicitly prefers Siren. Negotiable JSON, Siren, and 304
    responses vary on Accept even when the original response object is returned.
    Unmatched errors also pass through: the bridge does not infer API ownership from URL prefixes.

    Transformed responses retain cookies and semantic or security headers, and discard validators,
    digests, encodings, ranges, and framing tied to the source JSON bytes. Place Django's
    ConditionalGetMiddleware before this middleware so it evaluates the final Siren representation on
    the response path; a downstream 304 remains untouched because its representation body is unavailable.

    When source and public paths differ, the middleware maps a matched public route to its compiled
    source route before Django dispatch and restores the public request path before projection.
    """

    get_response: Callable[[object], object]
    adapter: SirenAdapter
    policy: SirenCapabilityPolicy | Callable[..., SirenAdapterPolicy]

    def __call__(self, request: object) -> object:
        match = self.adapter.match(request.method, request.path)
        dispatch_path = self.adapter.dispatch_path(
            request.method, request.path)
        original_path = request.path
        original_path_info = request.path_info
        if dispatch_path is not None:
            request.path = dispatch_path
            request.path_info = dispatch_path
        try:
            response = self.get_response(request)
        finally:
            request.path = original_path
            request.path_info = original_path_info
        if match is None:
            return response
        from django.utils.cache import patch_vary_headers

        if response.status_code == 304:
            patch_vary_headers(response, ("Accept",))
            return response
        if 300 <= response.status_code < 400:
            return response
        if getattr(response, "streaming", False):
            return response
        content_type = response.get(
            "Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type == "application/vnd.siren+json":
            patch_vary_headers(response, ("Accept",))
            return response
        content = bytes(response.content)
        if content and content_type != "application/json" and not content_type.endswith("+json"):
            return response
        patch_vary_headers(response, ("Accept",))
        accept = request.headers.get("Accept", "")
        if not SirenAccept(value=accept).selects_siren():
            return response
        result = json.loads(content) if content else None
        if isinstance(self.policy, SirenCapabilityPolicy):
            selected = self.policy.select(
                match.operation_id, response.status_code, request, result)
        else:
            selected = self.policy(
                match.operation_id, response.status_code, request, result)
        if not isinstance(selected, SirenAdapterPolicy):
            raise SirenityError(
                "Siren capability policy must return SirenAdapterPolicy")
        query = tuple((name, value)
                      for name in request.GET for value in request.GET.getlist(name))
        projected = self.adapter.respond(SirenAdapterRequest(
            operation_id=match.operation_id,
            method=request.method,
            path=request.path,
            status=response.status_code,
            result=result,
            base_url=request.build_absolute_uri("/").rstrip("/"),
            request_url=request.build_absolute_uri(),
            media_type=content_type if content else None,
            path_values=match.path_values,
            query=query,
            headers=dict(response.items()),
            policy=selected,
        ))
        from django.http import JsonResponse

        rendered = JsonResponse(
            projected.payload,
            status=projected.status,
            content_type=projected.media_type,
            headers=dict(projected.headers),
        )
        rendered.cookies = response.cookies
        return rendered
