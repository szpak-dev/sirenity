import os
import shutil
import subprocess
import sys
from pathlib import Path


class TestWiring:
    def test_service_check_rejects_an_injectable_missing_from_its_feature_export(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        package = workspace / "src/sirenity/contexts/shared/siren_schema/services/__init__.py"
        package.write_text(package.read_text().replace("from .reader import SirenSchemaReader\n", ""))

        result = self.command(workspace)

        assert result.returncode != 0
        assert "injectable SirenSchemaReader is not exported" in result.stdout

    def test_service_check_rejects_manual_container_construction_outside_wiring(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        service = workspace / "src/sirenity/contexts/runtime/routing/services/href.py"
        service.write_text(f"{service.read_text()}\ncreate_sync_container\n")

        result = self.command(workspace)

        assert result.returncode != 0
        assert "containers belong only in wiring.py" in result.stdout

    def test_service_check_rejects_a_collaborator_passed_through_a_service_method(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        service = workspace / "src/sirenity/contexts/compiler/assembly/services/api.py"
        service.write_text(
            service.read_text()
            + "\n    def rebuild(self, assembler: SirenApiAssembler) -> SirenApi:\n"
            + "        return assembler.assemble(())\n"
        )

        result = self.command(workspace)

        assert result.returncode != 0
        assert "SirenApiService.rebuild receives collaborator SirenApiAssembler as a method parameter" in result.stdout

    def test_service_check_rejects_direct_construction_of_an_injectable_collaborator(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        service = workspace / "src/sirenity/contexts/runtime/routing/services/href.py"
        service.write_text(
            service.read_text()
            + "\n    def resolver(self) -> None:\n"
            + "        SirenDefaultResourceResolver()\n"
        )

        result = self.command(workspace)

        assert result.returncode != 0
        assert "SirenDefaultHrefService constructs injectable SirenDefaultResourceResolver" in result.stdout

    def test_service_check_resolves_every_public_composition_entry_point(self):
        result = self.command(Path(__file__).parents[2])

        assert result.returncode == 0, result.stdout

    def command(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        python_path = os.pathsep.join((str(workspace / "src"), os.environ.get("PYTHONPATH", "")))
        return subprocess.run(
            (sys.executable, "scripts/check_service_conventions.py"),
            cwd=workspace,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": python_path},
            text=True,
        )

    def workspace(self, tmp_path: Path) -> Path:
        project = Path(__file__).parents[2]
        workspace = tmp_path / "workspace"
        shutil.copytree(project / "src", workspace / "src")
        shutil.copytree(project / "scripts", workspace / "scripts")
        return workspace
