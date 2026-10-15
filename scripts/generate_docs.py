import argparse
import importlib
import inspect
import pkgutil
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parents[1]
ORDER = re.compile(r"<!-- docs:order=(\d+) -->")


@dataclass(frozen=True)
class Guide:
    module: str
    title: str
    order: int
    path: Path


class DocumentationGenerator:
    @classmethod
    def project(cls) -> dict[str, object]:
        return tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]

    @classmethod
    def package(cls) -> object:
        package_name = str(cls.project()["name"]).replace("-", "_")
        return importlib.import_module(f"{package_name}.api")

    @classmethod
    def guides(cls, package: object) -> tuple[Guide, ...]:
        values = []
        for candidate in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            module = importlib.import_module(candidate.name)
            documentation = inspect.getdoc(module) or ""
            match = ORDER.search(documentation)
            if match is None:
                continue
            stem = candidate.name.rsplit(".", 1)[-1]
            section = "reference" if stem == "audit" else "how-to"
            title = documentation.splitlines()[0].rstrip(".")
            values.append(
                Guide(
                    module=module.__name__,
                    title=title or stem.replace("_", " ").title(),
                    order=int(match.group(1)),
                    path=ROOT / "docs" / section / f"{stem.replace('_', '-')}.md",
                )
            )
        return tuple(sorted(values, key=lambda guide: (guide.order, guide.module)))

    @classmethod
    def definitions(cls, package: object) -> tuple[tuple[str, object], ...]:
        return tuple((name, getattr(package, name)) for name in package.__all__)

    @classmethod
    def guide(cls, guide: Guide, definitions: tuple[tuple[str, object], ...]) -> str:
        sections = []
        for name, value in definitions:
            if getattr(value, "__module__", None) != guide.module:
                continue
            documentation = inspect.getdoc(value)
            if not documentation:
                raise ValueError(f"Public symbol {name} must have a docstring")
            sections.extend((f"## `{name}`", "", documentation, ""))
        return "\n".join((f"# {guide.title}", "", *sections)).rstrip() + "\n"

    @classmethod
    def reference(cls, definitions: tuple[tuple[str, object], ...]) -> str:
        directives = []
        for name, value in definitions:
            directive = "autoclass" if inspect.isclass(value) else "autofunction"
            directives.append(f".. {directive}:: {name}")
            if inspect.isclass(value):
                excluded = {"model_config"}
                decorators = getattr(value, "__pydantic_decorators__", None)
                if decorators is not None:
                    for group in (
                        decorators.validators,
                        decorators.field_validators,
                        decorators.model_validators,
                        decorators.field_serializers,
                        decorators.model_serializers,
                        decorators.computed_fields,
                    ):
                        excluded.update(group)
                directives.extend(
                    (
                        "   :members:",
                        "   :undoc-members:",
                        "   :member-order: bysource",
                        f"   :exclude-members: {', '.join(sorted(excluded))}",
                    )
                )
            directives.append("")
        return "\n".join(
            (
                "# Public API",
                "",
                "The supported surface is generated from `sirenity.api.__all__`. Import these names from",
                "`sirenity`; the defining modules remain implementation details.",
                "",
                "```{eval-rst}",
                ".. currentmodule:: sirenity.api",
                "",
                *directives,
                "```",
                "",
            )
        )

    @staticmethod
    def update(path: Path, expected: str, check: bool) -> bool:
        current = path.read_text() if path.exists() else ""
        if current == expected:
            return True
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected)
        return False

    @classmethod
    def run(cls, check: bool) -> int:
        package = cls.package()
        guides = cls.guides(package)
        definitions = cls.definitions(package)
        targets = [(guide.path, cls.guide(guide, definitions)) for guide in guides]
        targets.append((ROOT / "docs" / "reference" / "api.md", cls.reference(definitions)))
        stale = [path for path, expected in targets if not cls.update(path, expected, check)]
        if check and stale:
            print("Generated documentation is stale:")
            for path in stale:
                print(f"- {path.relative_to(ROOT)}")
            print("Run `make docs` and commit the result.")
            return 1
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate convention-discovered public documentation.")
    parser.add_argument("--check", action="store_true", help="Fail instead of updating stale documentation.")
    raise SystemExit(DocumentationGenerator.run(parser.parse_args().check))
