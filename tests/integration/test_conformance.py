import subprocess
import sys
import tarfile
from copy import deepcopy
from pathlib import Path

import pytest

from sirenity import SirenContext, SirenityError, siren

from ..framework_fixtures.django_ninja_extra.openapi_fixture import DjangoNinjaExtraOpenApiFixture
from ..framework_fixtures.fastapi.openapi_fixture import FastApiOpenApiFixture


class TestConformance:
    def test_public_facade_compiles_a_fastapi_controller_openapi_document(self):
        openapi = FastApiOpenApiFixture().document()

        document = siren(openapi).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                capabilities=frozenset({"list_example_resources"}),
            )
        )
        document = document.model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {
                "title": "Response Get Example Resource",
                "rel": ["self"],
                "href": "https://api.example.com/api/v1/example_resources",
            }
        ]
        assert document["actions"] == [
            {
                "name": "list_example_resources",
                "href": "https://api.example.com/api/v1/example_resources",
                "method": "GET",
                "title": "List example resources",
                "type": "application/x-www-form-urlencoded",
                "fields": [{"name": "page", "type": "number", "title": "Page", "value": 1}],
            }
        ]

        entity = siren(openapi).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                value={"id": "42"},
                capabilities=frozenset({"rename_example_resource"}),
            )
        )
        entity = entity.model_dump(by_alias=True, mode="json", exclude_none=True)

        assert entity["links"] == [
            {
                "title": "Response Get Example Resource",
                "rel": ["self"],
                "href": "https://api.example.com/api/v1/example_resources/42",
            }
        ]
        assert entity["actions"] == [
            {
                "name": "rename_example_resource",
                "href": "https://api.example.com/api/v1/example_resources/42",
                "method": "PATCH",
                "title": "Rename example resource",
                "type": "application/json",
                "fields": [{"name": "title", "type": "text", "title": "Title", "value": ""}],
            }
        ]

    def test_public_facade_compiles_a_django_ninja_extra_controller_openapi_document(self):
        openapi = DjangoNinjaExtraOpenApiFixture().document()

        assert 200 in openapi["paths"]["/api/v1/example_resources"]["get"]["responses"]

        invalid = deepcopy(openapi)
        invalid["paths"]["/api/v1/example_resources"]["get"]["responses"] = {999: {"description": "Invalid"}}

        with pytest.raises(SirenityError):
            siren(invalid)

        document = siren(openapi).project(
            SirenContext(
                base_url="https://api.example.com",
                scope="collection",
                resource="example_resource",
                capabilities=frozenset({"list_example_resources"}),
            )
        )
        document = document.model_dump(by_alias=True, mode="json", exclude_none=True)

        assert document["links"] == [
            {
                "title": "Response",
                "rel": ["self"],
                "href": "https://api.example.com/api/v1/example_resources",
            }
        ]
        assert document["actions"] == [
            {
                "name": "list_example_resources",
                "href": "https://api.example.com/api/v1/example_resources",
                "method": "GET",
                "title": "List example resources",
                "type": "application/x-www-form-urlencoded",
                "fields": [{"name": "page", "type": "number", "title": "Page", "value": 1}],
            }
        ]

        entity = siren(openapi).project(
            SirenContext(
                base_url="https://api.example.com",
                resource="example_resource",
                value={"id": "42"},
                capabilities=frozenset({"rename_example_resource"}),
            )
        )
        entity = entity.model_dump(by_alias=True, mode="json", exclude_none=True)

        assert entity["links"] == [
            {
                "title": "Response",
                "rel": ["self"],
                "href": "https://api.example.com/api/v1/example_resources/42",
            }
        ]
        assert entity["actions"] == [
            {
                "name": "rename_example_resource",
                "href": "https://api.example.com/api/v1/example_resources/42",
                "method": "PATCH",
                "title": "Rename example resource",
                "type": "application/json",
                "fields": [{"name": "title", "type": "text", "title": "Title", "value": ""}],
            }
        ]

    def test_built_wheel_supports_the_documented_public_consumer_flow(self, tmp_path: Path):
        project = Path(__file__).parents[2]
        artifacts = tmp_path / "artifacts"
        environment = tmp_path / "consumer"
        example_shared_installation = tmp_path / "example-shared-installation"
        fixture = project / "tests" / "fixtures" / "wheel_consumer.py"
        example_shared_fixture = (
            project / "tests" / "fixtures" / "wheel_example_django_mcp_consumer.py"
        )
        example_shared_source = example_shared_fixture.read_text()
        assert ".adapter.routes" not in example_shared_source
        assert "render_path" not in example_shared_source
        assert "example_operation.method" in example_shared_source
        assert "example_operation.dispatch_path" in example_shared_source
        subprocess.run(
            (sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(artifacts)),
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        )
        wheel = next(artifacts.glob("*.whl"))
        source = next(artifacts.glob("*.tar.gz"))

        with tarfile.open(source) as distribution:
            names = tuple(distribution.getnames())

        assert any(name.endswith("tests/framework_fixtures/fastapi/openapi_fixture.py") for name in names)
        assert any(name.endswith("tests/framework_fixtures/fastapi/example_resource_controller.py") for name in names)
        assert any(
            name.endswith("tests/framework_fixtures/fastapi/rename_example_resource_payload.py") for name in names
        )
        assert any(name.endswith("tests/framework_fixtures/django_ninja_extra/openapi_fixture.py") for name in names)
        assert any(
            name.endswith("tests/framework_fixtures/django_ninja_extra/example_resource_controller.py")
            for name in names
        )
        assert any(
            name.endswith("tests/framework_fixtures/django_ninja_extra/rename_example_resource_payload.py")
            for name in names
        )

        subprocess.run(
            (sys.executable, "-m", "venv", "--system-site-packages", str(environment)),
            check=True,
            capture_output=True,
            text=True,
        )
        consumer = environment / "bin" / "python"
        subprocess.run(
            (str(consumer), "-m", "pip", "install", str(wheel)),
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            (str(consumer), str(fixture)),
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert "site-packages/sirenity" in result.stdout
        subprocess.run(
            (
                str(consumer),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--target",
                str(example_shared_installation),
                str(wheel),
            ),
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        example_bootstrap = (
            "import importlib,sys;"
            "sys.path[:0]=sys.argv[1:3];"
            "importlib.import_module('wheel_example_django_mcp_consumer')"
        )
        example_shared_result = subprocess.run(
            (
                sys.executable,
                "-I",
                "-c",
                example_bootstrap,
                str(example_shared_installation),
                str(example_shared_fixture.parent),
            ),
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert example_shared_result.returncode == 0, example_shared_result.stderr
        assert str(example_shared_installation) in example_shared_result.stdout
