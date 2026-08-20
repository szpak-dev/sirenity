from django.http import JsonResponse


class DjangoExampleResourceView:
    def __call__(self, request, example_resource_id):
        return JsonResponse({"example_resource_id": example_resource_id, "title": "Example installed"})


django_example_resource_view = DjangoExampleResourceView()
