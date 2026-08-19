from pathlib import Path


class TestQualityGate:
    def test_ci_runs_the_complete_quality_gate_and_retains_package_evidence(self):
        project = Path(__file__).parents[2]
        workflow = (project / ".github/workflows/ci.yml").read_text()
        makefile = (project / "Makefile").read_text()
        pyproject = (project / "pyproject.toml").read_text()

        assert "DUMP ?= .dump" in makefile
        assert "UV_CACHE_DIR" in makefile
        assert "PYTHONPYCACHEPREFIX" in makefile
        assert "quality: verify package-check" in makefile
        assert "rm -rf dist/quality" in makefile
        assert "$(RUN) -m build --wheel --sdist --outdir dist/quality" in makefile
        assert "$(RUN) -m twine check dist/quality/*" in makefile
        assert "- run: make quality" in workflow
        assert "uv sync --locked --all-groups" in workflow
        assert "astral-sh/setup-uv" in workflow
        assert "UV_CACHE_DIR: ${{ github.workspace }}/.dump/uv-cache" in workflow
        assert 'cache_dir = ".dump/pytest-cache"' in pyproject
        assert 'cache-dir = ".dump/ruff-cache"' in pyproject
        assert "python -m pip install -e \".[dev]\"" not in workflow
        assert "if: always()" in workflow
        assert "path: dist/quality/" in workflow
