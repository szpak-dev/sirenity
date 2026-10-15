import inspect
from importlib import import_module

from sphinx.errors import ConfigError

project = "Sirenity"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_external_toc",
]

source_suffix = {".md": "markdown"}
root_doc = "index"
external_toc_path = "_toc.yml"
external_toc_exclude_missing = True

autodoc_typehints = "none"
nitpicky = True

myst_enable_extensions = ["colon_fence", "deflist"]

exclude_patterns = ["_build"]
html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/szpak-dev/sirenity/",
    "source_branch": "main",
    "source_directory": "docs/",
}

public_api = import_module("sirenity.api")
exports = tuple(public_api.__all__)
if not exports:
    raise ConfigError("sirenity.api.__all__ must publish at least one name")
if len(exports) != len(set(exports)):
    raise ConfigError("sirenity.api.__all__ must contain unique names")
missing_exports = tuple(name for name in exports if not hasattr(public_api, name))
if missing_exports:
    raise ConfigError(f"sirenity.api.__all__ contains unresolved names: {missing_exports!r}")


def summarize_public_api_docstrings(app, what, name, obj, options, lines):
    """Render safe summaries while the full Markdown docstrings stay in the integration guides."""
    if name != "sirenity.api" and not name.startswith("sirenity.api."):
        return
    documentation = inspect.getdoc(obj) or ""
    summary = " ".join(documentation.split("\n\n", 1)[0].split())
    if not summary or summary.startswith("!!! abstract") or summary == "Base class for protocol classes.":
        lines.clear()
        return
    summary = summary.replace(":func:", "").replace(":class:", "").replace("`", "")
    lines[:] = [summary]


def setup(app):
    """Register documentation-only Sphinx behavior."""
    app.connect("autodoc-process-docstring", summarize_public_api_docstrings)
