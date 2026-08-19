# Shared configuration

## `siren_configuration`

Resolve one immutable, shared Siren integration configuration.

Pass dotted paths for an OpenAPI provider, explicit capability policy, and optional adapter
profiles. Resolution and compilation occur exactly once when this configuration is created;
``adapter()`` and ``django(get_response)`` reuse that compiled graph for its lifetime.

```python
from sirenity import siren_configuration

configuration = siren_configuration(
    openapi="example_project.api.openapi_schema",
    source_path="/api",
    public_path="/siren",
    policy="example_project.permissions.siren_policy",
    profiles=("sirenity.SirenStructuredFormProfile",),
)
adapter = configuration.adapter()
middleware = configuration.django(get_response)
```

Use the same configuration for every supported integration. Django settings create a fresh
configuration for each startup, autoreload, and overridden-settings lifecycle, so stale
process-global graphs are never reused.
