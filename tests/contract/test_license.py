import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_distribution_is_explicitly_proprietary() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert project["license"] == "LicenseRef-Proprietary"
    assert project["license-files"] == ["LICENSE"]
    assert not any(classifier.startswith("License ::") for classifier in project["classifiers"])
    assert "All rights reserved" in license_text
    assert "No license or other rights are granted" in license_text
    assert "Any unauthorized use is strictly prohibited" in license_text


def test_generated_documentation_links_complete_license_terms() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "[LICENSE](LICENSE)" in readme
    assert "[License](../LICENSE)" in index
