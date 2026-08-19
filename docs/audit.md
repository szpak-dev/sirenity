# Compatibility audit

## `audit`

Inspect a valid OpenAPI document against the current official-Siren support boundary.

Call this during startup before `siren(openapi)` when a consumer needs every currently
unsupported construct at once. The report exposes typed findings and `render()` for terminal
or CI output; `siren(openapi)` remains the strict fail-fast compilation entry point.
