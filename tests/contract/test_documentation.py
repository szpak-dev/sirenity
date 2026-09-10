from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_generated_navigation_links_the_current_architecture_baseline() -> None:
    architecture = ROOT / "docs" / "architecture.md"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert architecture.is_file()
    assert "[Current architecture](docs/architecture.md)" in readme
    assert "[Current architecture](architecture.md)" in index
