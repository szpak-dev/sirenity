import shutil
from pathlib import Path

from scripts.check_service_conventions import ServiceConventionChecker


class TestWiring:
    def test_service_check_rejects_an_injectable_missing_from_its_feature_export(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        package = workspace / "src/sirenity/contexts/shared/siren_schema/services/__init__.py"
        package.write_text(package.read_text().replace("from .reader import SirenSchemaReader\n", ""))

        failures = self.failures(workspace)

        assert any("injectable SirenSchemaReader is not exported" in failure for failure in failures)

    def test_service_check_rejects_manual_container_construction_outside_wiring(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        service = workspace / "src/sirenity/contexts/runtime/routing/services/href.py"
        service.write_text(f"{service.read_text()}\ncreate_sync_container\n")

        failures = self.failures(workspace)

        assert any("containers belong only in wiring.py" in failure for failure in failures)

    def test_service_check_rejects_a_collaborator_passed_through_a_service_method(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        service = workspace / "src/sirenity/contexts/compiler/assembly/services/api.py"
        service.write_text(
            service.read_text()
            + "\n    def rebuild(self, assembler: SirenApiAssembler) -> SirenApi:\n"
            + "        return assembler.assemble(())\n"
        )

        failures = self.failures(workspace)

        assert any(
            "SirenApiService.rebuild receives collaborator SirenApiAssembler as a method parameter" in failure
            for failure in failures
        )

    def test_service_check_rejects_direct_construction_of_an_injectable_collaborator(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        service = workspace / "src/sirenity/contexts/runtime/routing/services/href.py"
        service.write_text(
            service.read_text() + "\n    def resolver(self) -> None:\n" + "        SirenDefaultResourceResolver()\n"
        )

        failures = self.failures(workspace)

        assert any(
            "SirenDefaultHrefService constructs injectable SirenDefaultResourceResolver" in failure
            for failure in failures
        )

    def test_service_check_resolves_every_public_composition_entry_point(self):
        project = Path(__file__).parents[2]
        failures = ServiceConventionChecker(project / "src" / "sirenity").violations()

        assert failures == ()

    def failures(self, workspace: Path) -> tuple[str, ...]:
        return ServiceConventionChecker(
            workspace / "src" / "sirenity",
            include_composition=False,
        ).violations()

    def workspace(self, tmp_path: Path) -> Path:
        project = Path(__file__).parents[2]
        workspace = tmp_path / "workspace"
        shutil.copytree(project / "src", workspace / "src")
        shutil.copytree(project / "scripts", workspace / "scripts")
        return workspace
