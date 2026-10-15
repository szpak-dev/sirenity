import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MarkdownPythonExamples:
    path: Path

    pattern = re.compile(r"^```python\n(.*?)^```$", re.MULTILINE | re.DOTALL)

    def source(self) -> str:
        content = self.path.read_text(encoding="utf-8")
        blocks = tuple(match.group(1) for match in self.pattern.finditer(content))
        if not blocks:
            raise ValueError(f"No Python examples found in {self.path}")
        return "\n\n".join(blocks)

    def execute(self) -> None:
        source = self.source()
        code = compile(source, str(self.path), "exec")
        exec(code, {"__name__": "__documentation_example__"})


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tutorial = root / "docs" / "tutorials" / "openapi-to-siren.md"
    MarkdownPythonExamples(tutorial).execute()
    print(f"Documentation examples: {tutorial.relative_to(root)} passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
