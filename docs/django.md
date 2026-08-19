# Django integration

## `SirenMiddleware`

Install Siren through Django's standard middleware loader.

The loader turns the current ``SIRENITY`` settings into one immutable public configuration,
then installs middleware from that same configuration. Each Django startup, autoreload process,
and ``override_settings`` lifecycle therefore receives a fresh resolved configuration without a
process-global adapter. ``OPENAPI`` and ``POLICY`` are dotted import paths; ``PROFILES`` is an
optional sequence of profile paths. A missing policy retains the standard allow-all behavior.
