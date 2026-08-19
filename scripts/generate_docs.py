import argparse
import importlib
import inspect
import pkgutil
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).parents[1]
START = "<!-- generated:public-api:start -->"
END = "<!-- generated:public-api:end -->"
ORDER = re.compile(r"<!-- docs:order=(\d+) -->")


class AnnotationText(str):
    def __repr__(self) -> str:
        return str(self)


@dataclass(frozen=True)
class Guide:
    module: str
    title: str
    order: int
    path: Path


class DocumentationGenerator:
    @classmethod
    def package(cls) -> object:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        return importlib.import_module(project["project"]["name"].replace("-", "_"))

    @classmethod
    def guides(cls, package: object) -> tuple[Guide, ...]:
        values = []
        for candidate in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            module = importlib.import_module(candidate.name)
            documentation = inspect.getdoc(module) or ""
            match = ORDER.search(documentation)
            if match is None:
                continue
            title = documentation.splitlines()[0].rstrip(".")
            values.append(Guide(
                module=module.__name__,
                title=title or candidate.name.rsplit(".", 1)[-1].replace("_", " ").title(),
                order=int(match.group(1)),
                path=ROOT / "docs" / f"{candidate.name.rsplit('.', 1)[-1]}.md",
            ))
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
    def reference(cls, package: object, definitions: tuple[tuple[str, object], ...]) -> str:
        rows = []
        for name, value in definitions:
            rows.append(f"| `{name}` | {cls.purpose(name, value)} | {cls.operations(value)} |")
        return "\n".join((
            "# Public API reference",
            "",
            f"The supported root imports below are generated from `{package.__name__}.__all__`.",
            "",
            "| Symbol | Purpose | Primary API |",
            "| --- | --- | --- |",
            *rows,
            "",
        ))

    @staticmethod
    def purpose(name: str, value: object) -> str:
        if name == "__version__":
            return "Installed distribution version."
        documentation = inspect.getdoc(value)
        if not documentation:
            raise ValueError(f"Public symbol {name} must have a docstring")
        return documentation.splitlines()[0]

    @staticmethod
    def operations(value: object) -> str:
        if not inspect.isclass(value):
            return "—"
        decorators = getattr(value, "__pydantic_decorators__", None)
        validators = decorators.model_validators if decorators is not None else {}
        operations = []
        for name, member in value.__dict__.items():
            if name.startswith("_") or name in validators:
                continue
            if isinstance(member, property):
                annotation = DocumentationGenerator.annotation(inspect.signature(member.fget).return_annotation)
                operations.append(f"`{name}: {annotation}`")
                continue
            if not callable(getattr(value, name, None)):
                continue
            signature = DocumentationGenerator.signature(getattr(value, name))
            parameters = tuple(signature.parameters.values())
            if parameters and parameters[0].name in {"self", "cls"}:
                signature = signature.replace(parameters=parameters[1:])
            operations.append(f"`{name}{signature}`")
        return "<br>".join(operations) or "—"

    @staticmethod
    def signature(value: object) -> inspect.Signature:
        signature = inspect.signature(value)
        parameters = tuple(parameter.replace(
            annotation=DocumentationGenerator.annotation(parameter.annotation),
            default=DocumentationGenerator.default(parameter.default),
        ) for parameter in signature.parameters.values())
        return signature.replace(
            parameters=parameters,
            return_annotation=DocumentationGenerator.annotation(signature.return_annotation),
        )

    @staticmethod
    def annotation(value: object) -> object:
        if value is inspect.Signature.empty:
            return value
        text = value if isinstance(value, str) else str(value)
        return AnnotationText(re.sub(r"(?<![.\w])Any(?![\w])", "typing.Any", text))

    @staticmethod
    def default(value: object) -> object:
        if value is inspect.Parameter.empty:
            return value
        if isinstance(value, str | int | float | bool | tuple | dict | type(None)):
            return value
        return AnnotationText(f"<{type(value).__module__}.{type(value).__qualname__}>")

    @staticmethod
    def navigation(guides: tuple[Guide, ...], prefix: str = "") -> tuple[str, ...]:
        return tuple(f"- [{guide.title}]({prefix}{guide.path.name})" for guide in guides)

    @classmethod
    def readme(cls, current: str, guides: tuple[Guide, ...]) -> str:
        generated = "\n".join((
            START,
            "## Documentation",
            "",
            "Guides are generated from marked public modules. Run `make docs` after changing public guidance.",
            "",
            *cls.navigation(guides, "docs/"),
            "- [Public API reference](docs/reference.md)",
            END,
        ))
        if START not in current or END not in current:
            raise ValueError("Missing generated documentation markers in README.md")
        prefix, remainder = current.split(START, 1)
        _, suffix = remainder.split(END, 1)
        return f"{prefix}{generated}{suffix}"

    @classmethod
    def index(cls, guides: tuple[Guide, ...]) -> str:
        return "\n".join((
            "# Sirenity documentation",
            "",
            "- [Overview](../README.md)",
            *cls.navigation(guides),
            "- [Public API reference](reference.md)",
            "",
        ))

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
        targets = [(ROOT / "README.md", cls.readme((ROOT / "README.md").read_text(), guides))]
        targets.append((ROOT / "docs" / "index.md", cls.index(guides)))
        targets.append((ROOT / "docs" / "reference.md", cls.reference(package, definitions)))
        targets.extend((guide.path, cls.guide(guide, definitions)) for guide in guides)
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
