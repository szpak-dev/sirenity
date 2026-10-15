# Sirenity

Sirenity compiles an OpenAPI 3.1 document into a reusable Siren engine. At request time, the engine combines
application data with explicit capabilities and returns a hypermedia response containing concrete links and the
actions currently available to the caller.

The application still owns authentication, authorization policy, and operation execution. Sirenity owns the
OpenAPI compilation, route matching, input placement, and translation into Siren or typed MCP results.

## Install

Sirenity requires Python 3.12 or later.

```console
python -m pip install sirenity
```

Compile the OpenAPI document once during startup, then project application values through the resulting engine:

```python
from sirenity import SirenContext, siren

engine = siren(openapi, source_path="/api", public_path="/siren")
document = engine.project(
    SirenContext(
        base_url="https://api.example.com",
        resource="record",
        value={"id": "record-42", "title": "Architecture"},
        capabilities=frozenset({"get_record", "rename_record"}),
    )
)
```

The [first OpenAPI-to-Siren tutorial](docs/tutorials/openapi-to-siren.md) supplies a complete document and shows the
projected result.

## Documentation

- [Documentation entrance](docs/index.md)
- [Tutorials](docs/tutorials/index.md)
- [How-to guides](docs/how-to/index.md)
- [Explanations](docs/explanation/index.md)
- [Architecture](docs/explanation/architecture.md)
- [Glossary](docs/reference/glossary.md)
- [Technical reference](docs/reference/index.md)

## Development

```console
uv sync --locked --all-groups
make verify
```

Build the documentation with `make docs-check`. Generated HTML is written below `docs/_build` and remains outside
source control.

## License

Sirenity is proprietary software. No permission to use, copy, modify, or distribute it is granted without prior
express written permission. See [LICENSE](LICENSE) for the complete terms.
