import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sirenity.wiring import SirenApplicationContainer


class SirenSpecCommand:
    def verify_evidence(self, cucumber_report: Path, feature_directory: Path) -> str:
        conformance = SirenApplicationContainer().application().conformance_service()
        report = conformance.inspect(cucumber_report, feature_directory)
        rendered = conformance.render(report)
        print(rendered)
        conformance.verify(report)
        return rendered

    def run(self) -> int:
        with TemporaryDirectory() as directory:
            cucumber_report = Path(directory) / "cucumber.json"
            result = subprocess.run(
                (
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/conformance",
                    "--cucumberjson",
                    str(cucumber_report),
                    "--junitxml",
                    str(cucumber_report.with_name("junit.xml")),
                    "-q",
                ),
                capture_output=True,
                text=True,
            )
            if result.returncode:
                sys.stderr.write(result.stdout)
                sys.stderr.write(result.stderr)
                return result.returncode
            self.verify_evidence(cucumber_report, Path("tests/conformance/features"))
        return 0


if __name__ == "__main__":
    raise SystemExit(SirenSpecCommand().run())
