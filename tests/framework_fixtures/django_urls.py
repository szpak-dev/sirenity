from django.urls import path

from .django_example_resource_view import django_example_resource_view
from .django_root_view import django_root_view

urlpatterns = [
    path("api/", django_root_view),
    path("api/example_resources/<str:example_resource_id>", django_example_resource_view),
]
