import importlib
import inspect
import re
import runpy
import typing
from pathlib import Path

from django.conf import settings
from django.test import RequestFactory, override_settings

from sirenity import SirenMiddleware


class TestDocumentedIntegrations:
    def test_example_project_boundaries_are_fully_typed(self, monkeypatch):
        project = Path(__file__).parents[2]
        monkeypatch.syspath_prepend(str(project / "tests" / "fixtures"))
        example_api = importlib.import_module("example_project.api")
        example_application = importlib.import_module("example_project.application")
        example_execution = importlib.import_module("example_project.execution")
        example_permissions = importlib.import_module("example_project.permissions")

        boundaries = (
            example_api.openapi_schema,
            example_application.example_get_response,
            example_execution.ExampleMcpExecutor.execute,
            example_permissions.siren_policy,
        )
        for boundary in boundaries:
            annotations = typing.get_type_hints(boundary)
            signature = inspect.signature(boundary)
            assert "return" in annotations
            assert all(
                parameter.name == "self" or parameter.name in annotations
                for parameter in signature.parameters.values()
            )
        assert typing.get_type_hints(example_permissions.siren_policy)["operation_id"] is str

    def test_readme_examples_are_the_executable_fixture_files(self, monkeypatch):
        project = Path(__file__).parents[2]
        monkeypatch.syspath_prepend(str(project / "tests" / "fixtures"))
        readme = (project / "README.md").read_text()
        fixtures = project / "tests" / "fixtures" / "documented_integrations"

        for name, path in (
            ("framework-neutral", fixtures / "framework_neutral.py"),
            ("django", fixtures / "django_settings.py"),
            ("django-mcp", fixtures / "django_mcp.py"),
        ):
            match = re.search(
                rf"<!-- example:{name}:start -->\n```python\n(.*?)\n```\n<!-- example:{name}:end -->",
                readme,
                re.DOTALL,
            )
            assert match is not None
            assert match.group(1) + "\n" == path.read_text()
            assert re.findall(r"from (sirenity(?:\.[\w.]+)?) import", match.group(1)) in ([], ["sirenity"])

    def test_framework_neutral_example_projects_an_observable_siren_response(self, monkeypatch):
        project = Path(__file__).parents[2]
        monkeypatch.syspath_prepend(str(project / "tests" / "fixtures"))

        values = runpy.run_path(
            str(project / "tests" / "fixtures" / "documented_integrations" / "framework_neutral.py")
        )

        assert values["example_response"].media_type == "application/vnd.siren+json"
        assert values["example_response"].payload["properties"] == {
            "example_resource_id": "example-resource-42",
            "title": "Updated example resource",
        }

    def test_standard_django_example_negotiates_the_public_mount(self, monkeypatch):
        project = Path(__file__).parents[2]
        monkeypatch.syspath_prepend(str(project / "tests" / "fixtures"))
        if not settings.configured:
            settings.configure(DEFAULT_CHARSET="utf-8", ALLOWED_HOSTS=["testserver"])
        values = runpy.run_path(
            str(project / "tests" / "fixtures" / "documented_integrations" / "django_settings.py")
        )

        with override_settings(
            ALLOWED_HOSTS=["testserver"],
            SIRENITY=values["SIRENITY"],
        ):
            example_application = importlib.import_module("example_project.application")
            middleware = SirenMiddleware(example_application.example_get_response)
            request = RequestFactory().patch(
                "/siren/example_resources/example-resource-42",
                data={"title": "Updated example resource", "metadata": {"source": "example"}},
                content_type="application/json",
                HTTP_ACCEPT="application/vnd.siren+json",
                HTTP_EXAMPLE_TRACE="example-trace",
                HTTP_COOKIE="example_session=example-session",
            )
            response = middleware(request)

        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/vnd.siren+json")

    def test_shared_django_mcp_example_normalizes_inputs_and_handles_failure(self, monkeypatch):
        project = Path(__file__).parents[2]
        monkeypatch.syspath_prepend(str(project / "tests" / "fixtures"))
        example_api = importlib.import_module("example_project.api")
        example_api.calls = 0

        values = runpy.run_path(
            str(project / "tests" / "fixtures" / "documented_integrations" / "django_mcp.py")
        )
        example_application = importlib.import_module("example_project.application")

        with override_settings(SIRENITY=values["SIRENITY"]):
            example_django = SirenMiddleware(example_application.example_get_response)

        assert example_api.calls == 1
        assert example_django.middleware.adapter is values["example_configuration"].adapter()
        assert values["example_mcp"].adapter is values["example_configuration"].adapter()
        assert values["example_result"].is_error is False
        assert values["example_result"].structured_content["properties"] == {
            "example_resource_id": "example-resource-42",
            "title": "Updated example resource",
            "metadata": {"source": "example"},
            "example_page": 2,
            "example_trace": "example-trace",
            "example_session": "example-session",
        }
        assert values["example_error"] == {"detail": "Siren MCP invocation is invalid"}
