import re
import subprocess
import sys
import tempfile
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

    def execute_as_script(self, name: str, root: Path) -> None:
        source = self.source()
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / name
            script.write_text(source, encoding="utf-8")
            subprocess.run((sys.executable, str(script)), cwd=root, check=True)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    direct = root / "docs" / "tutorials" / "openapi-to-siren.md"
    typed_navigation = root / "docs" / "tutorials" / "typed-mcp-navigation.md"
    MarkdownPythonExamples(direct).execute()
    MarkdownPythonExamples(typed_navigation).execute_as_script("typed_navigation.py", root)
    print(
        "Documentation examples: "
        f"{direct.relative_to(root)} and {typed_navigation.relative_to(root)} passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
