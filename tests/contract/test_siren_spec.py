import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class TestSirenSpecCommand:
    def test_command_fails_when_the_committed_gherkin_inventory_has_duplicates(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        feature = workspace / "tests/conformance/features/relations.feature"
        shutil.copy2(feature, feature.with_name("relations_copy.feature"))

        result = self.command(workspace)

        assert result.returncode != 0
        assert "Gherkin feature inventory contains duplicate scenarios." in result.stderr

    def test_command_fails_when_a_committed_scenario_has_no_cucumber_evidence(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        (workspace / "tests/conformance/steps/test_relation_steps.py").unlink()

        result = self.command(workspace)

        assert result.returncode != 0
        assert "Cucumber report is missing committed scenarios: Siren relations:" in result.stderr

    def test_command_fails_when_junit_contains_a_non_cucumber_testcase(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        evidence = workspace / "tests/conformance/test_unmapped_evidence.py"
        evidence.write_text("def test_unmapped_evidence() -> None:\n    pass\n")

        result = self.command(workspace)

        assert result.returncode != 0
        assert "JUnit report contains non-Cucumber testcases: test_unmapped_evidence." in result.stderr

    def test_command_fails_when_junit_contains_an_ordinary_skip(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        evidence = workspace / "tests/conformance/test_skipped_evidence.py"
        evidence.write_text(
            'import pytest\n\n\ndef test_skipped_evidence() -> None:\n    pytest.skip("ordinary skip")\n'
        )

        result = self.command(workspace)

        assert result.returncode != 0
        assert "JUnit report contains a skipped test that is not a strict expected failure." in result.stderr

    def test_command_fails_when_an_expected_failure_unexpectedly_passes(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        evidence = workspace / "tests/conformance/test_xpass_evidence.py"
        evidence.write_text(
            "import pytest\n\n\n"
            '@pytest.mark.xfail(reason="tracked expected failure")\n'
            "def test_xpass_evidence() -> None:\n"
            "    pass\n"
        )

        result = self.command(workspace)

        assert result.returncode != 0
        assert "XPASS" in result.stderr

    def test_command_fails_after_a_public_schema_narrows_an_official_requirement(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        field_value = workspace / "src/sirenity/contexts/runtime/document/values/field_value.py"
        field_value.write_text(
            field_value.read_text().replace("value: str | StrictInt | StrictFloat", "value: str | StrictInt")
        )

        result = self.command(workspace)

        assert result.returncode != 0
        assert "✗ FieldValueObject.value — structural contract" in result.stdout
        assert "Siren conformance ledger has unimplemented structural requirements:" in result.stderr
        assert "FieldValueObject.value." in result.stderr

    def test_command_fails_for_an_unsupported_official_schema_term(self, tmp_path: Path):
        workspace = self.workspace(tmp_path)
        schema = workspace / "src/sirenity/contexts/shared/siren_schema/values/siren.schema.json"
        document = json.loads(schema.read_text())
        document["definitions"]["Action"]["properties"]["href"]["minLength"] = 1
        schema.write_text(json.dumps(document))

        result = self.command(workspace)

        assert result.returncode != 0
        assert "Unsupported Siren schema terms: minLength" in result.stderr

    def test_command_prints_the_unified_siren_conformance_ledger(self):
        result = self.command(Path(__file__).parents[2])

        assert result.returncode == 0, result.stderr
        assert "Siren conformance ledger" in result.stdout
        assert "  Structural contract" in result.stdout
        assert "  Executable specification" in result.stdout
        assert "      ✓ Action.method.PATCH — structural contract" in result.stdout
        assert "      ✓ EmbeddedLinkSubEntity.rel — structural contract" in result.stdout
        assert "      ✓ EmbeddedRepresentationSubEntity.rel — structural contract" in result.stdout
        assert "      ✓ Link.rel — structural contract" in result.stdout
        assert "      ✓ Action.href — structural contract" in result.stdout
        assert "      ✓ Action.type — structural contract" in result.stdout
        assert "      ✓ EmbeddedLinkSubEntity.href — structural contract" in result.stdout
        assert "      ✓ EmbeddedLinkSubEntity.type — structural contract" in result.stdout
        assert "      ✓ Link.href — structural contract" in result.stdout
        assert "      ✓ Link.type — structural contract" in result.stdout
        assert "      ✓ A root entity serializes a self link — executable specification" in result.stdout
        assert "      ✓ Duplicate action names are rejected — executable specification" in result.stdout
        assert "      ✓ Duplicate field names are rejected — executable specification" in result.stdout
        assert "      ✓ An action with fields serializes its default type — executable specification" in result.stdout
        assert "      ✓ A link with a non-URI href is rejected — executable specification" in result.stdout
        definitions = tuple(
            line[4:] for line in result.stdout.splitlines() if line.startswith("    ") and not line.startswith("      ")
        )

        assert definitions[:7] == (
            "Entity",
            "EmbeddedLinkSubEntity",
            "EmbeddedRepresentationSubEntity",
            "Action",
            "Field",
            "FieldValueObject",
            "Link",
        )

    def command(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        python_path = os.pathsep.join((str(workspace / "src"), os.environ.get("PYTHONPATH", "")))
        return subprocess.run(
            ("make", "siren-spec"),
            cwd=workspace,
            capture_output=True,
            env={**os.environ, "PYTHON": sys.executable, "PYTHONPATH": python_path},
            text=True,
        )

    def workspace(self, tmp_path: Path) -> Path:
        project = Path(__file__).parents[2]
        workspace = tmp_path / "workspace"
        shutil.copytree(project / "src", workspace / "src")
        shutil.copytree(project / "tests/conformance", workspace / "tests/conformance")
        shutil.copytree(project / "scripts", workspace / "scripts")
        shutil.copy2(project / "Makefile", workspace / "Makefile")
        shutil.copy2(project / "pyproject.toml", workspace / "pyproject.toml")
        return workspace
