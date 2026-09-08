# Contributing

Keep contracts frozen, strict, explicit, and non-nullable. Constructors receive complete
dependencies, polymorphic collaborators use abstract base classes, OpenAPI remains the source of
truth for operations and routes, and feature packages are not export barrels.

Generated README regions project root `__all__` and public docstrings. Edit those sources and run
`make docs`; never hand-edit generated regions.

```bash
uv sync --all-groups --frozen
make verify-fast
```

Use the fast verification tier during development. Before review, run the complete gate:

```bash
make verify
```

## Releases

Hatch derives the distribution version from an exact `vX.Y.Z` Git tag. After the release PR has
merged, update local `main`, create the annotated release tag on that commit, push the tag, and
verify that `uv build` and `uv run twine check dist/*` produce valid matching wheel and
source-distribution versions. Never tag a pull request head.

After separately approving the artifacts, create the GitHub Release from that exact tag. The
release workflow builds and attaches release assets, then publishes them to PyPI through the
`pypi` environment gate.
