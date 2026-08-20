from django.http import HttpRequest, JsonResponse


def example_get_response(request: HttpRequest) -> JsonResponse:
    return JsonResponse({
        "example_resource_id": "example-resource-42",
        "title": "Updated example resource",
    })
