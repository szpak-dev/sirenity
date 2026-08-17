.PHONY: docs docs-check package-check quality service-check siren-spec verify

UV ?= uv
DUMP ?= .dump
export UV_CACHE_DIR := $(CURDIR)/$(DUMP)/uv-cache
export PYTHONPYCACHEPREFIX := $(CURDIR)/$(DUMP)/pycache
PYTHON ?= $(UV) run --locked python
RUN = PYTHONPATH=src $(PYTHON)

docs:
	$(RUN) scripts/generate_docs.py

docs-check:
	$(RUN) scripts/generate_docs.py --check

service-check:
	$(RUN) scripts/check_service_conventions.py

siren-spec:
	$(RUN) scripts/siren_spec.py

verify: docs-check service-check siren-spec
	$(RUN) -m ruff check .
	$(RUN) -m pytest

package-check:
	rm -rf dist/quality
	mkdir -p dist/quality
	$(RUN) -m build --wheel --sdist --outdir dist/quality
	$(RUN) -m twine check dist/quality/*

quality: verify package-check
