import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

from .contracts import ExampleContracts


class InstalledExamplePackage:
    def __init__(self):
        self.root = Path(__file__).parents[2]
        self.temporary = Path(tempfile.mkdtemp(prefix="sirenity-example-wheel-"))
        self.environment = self.temporary / "environment"
        self.python = self.environment / "bin" / "python"
        self.installed = False

    def install(self) -> None:
        if self.installed:
            return
        distribution = self.temporary / "distribution"
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(distribution)],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
        wheel = next(distribution.glob("sirenity-*.whl"))
        venv.EnvBuilder(with_pip=True).create(self.environment)
        subprocess.run(
            [str(self.python), "-m", "pip", "install", str(wheel)],
            cwd=self.temporary,
            check=True,
            capture_output=True,
            text=True,
        )
        self.installed = True

    def run(self, program: str) -> subprocess.CompletedProcess[str]:
        self.install()
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        environment["EXAMPLE_OPENAPI"] = json.dumps(ExampleContracts().bounded())
        return subprocess.run(
            [str(self.python), "-c", program],
            cwd=self.temporary,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )


EXAMPLE_INSTALLED_PACKAGE = InstalledExamplePackage()
