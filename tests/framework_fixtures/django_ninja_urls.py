from django.urls import path

from .django_ninja_api import django_ninja_api

urlpatterns = [path("", django_ninja_api.urls)]
