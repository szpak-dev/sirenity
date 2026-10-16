# Compatibility audit

## `audit`

Inspect a valid OpenAPI document against the current official-Siren support boundary.

### Run the compatibility gate

Call this during startup before `siren(openapi)` when a consumer needs every currently
unsupported construct at once. The report exposes typed findings and `render()` for terminal
or CI output; `siren(openapi)` remains the strict fail-fast compilation entry point.

```python
from sirenity import audit

openapi = {
    "openapi": "3.1.1",
    "info": {"title": "Example API", "version": "1.0.0"},
    "paths": {},
}
report = audit(openapi)
if not report.compatible:
    raise SystemExit(report.render())
```

A zero exit proves that the supplied JSON-compatible OpenAPI 3.1 document fits the current
compilation boundary. It does not validate application authorization, operation execution, or
business behavior.

### Support and maturity boundary

Sirenity requires Python 3.12 or later and currently declares development status Alpha. The
supported Python surface is the set of names exported from `sirenity`; private compiler and
runtime modules are not compatibility contracts. Default documents use official Siren members.
Optional profiles own their explicitly versioned extension metadata.

Run this audit and the consumer's public-behavior suite when upgrading Sirenity. A compatible
report establishes contract coverage for compilation, while successful application tests remain
the evidence for policy and execution behavior.
