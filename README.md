# sirenity

`sirenity` compiles a complete OpenAPI 3.1 document into a reusable Siren engine. At request
time, the engine turns application data and permissions into a Siren response with concrete links
and authorized actions.

Requires Python 3.12 or later.

## Install

```bash
python -m pip install sirenity
```

For local development, install `uv` and use the locked environment:

```bash
UV_CACHE_DIR=.dump/uv-cache uv sync --locked --all-groups
make verify
```

<!-- generated:public-api:start -->
## Documentation

Guides are generated from marked public modules. Run `make docs` after changing public guidance.

- [Siren compiler](docs/siren.md)
- [Framework-neutral adapter](docs/adapter.md)
- [Shared configuration](docs/configuration.md)
- [Django integration](docs/django.md)
- [MCP integration](docs/mcp.md)
- [Compatibility audit](docs/audit.md)
- [Public API reference](docs/reference.md)
<!-- generated:public-api:end -->
