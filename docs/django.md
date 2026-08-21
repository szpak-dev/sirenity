# Django integration

## `SirenMiddleware`

Install Siren through Django's standard middleware loader.

The loader consumes an exact immutable ``SirenConfiguration`` or turns the current ``SIRENITY``
mapping into one, then installs middleware from that same configuration. Resolved settings
declarations remain fresh for each Django startup, autoreload process, and ``override_settings``
lifecycle; a supplied configuration retains its caller-owned adapter lifecycle. ``OPENAPI`` and
``POLICY`` are dotted import paths; ``PROFILES`` is an optional sequence of profile paths. A
missing policy retains the standard allow-all behavior.
