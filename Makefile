.PHONY: docs docs-check docs-examples docs-generated docs-generated-check docs-linkcheck docs-links docs-lock package-check quality service-check siren-spec verify verify-fast

UV ?= uv
DUMP ?= .dump
export UV_CACHE_DIR := $(CURDIR)/$(DUMP)/uv-cache
export PYTHONPYCACHEPREFIX := $(CURDIR)/$(DUMP)/pycache
PYTHON ?= $(UV) run --locked python
RUN = PYTHONPATH=src $(PYTHON)

docs-generated:
	$(RUN) scripts/generate_docs.py

docs-generated-check:
	$(RUN) scripts/generate_docs.py --check

docs-links:
	$(UV) run --isolated --no-project --python 3.12 python scripts/check_docs_links.py

docs-examples:
	$(RUN) scripts/check_docs_examples.py

docs-check: docs-generated-check docs-links docs-examples
	rm -rf docs/_build/html
	PYTHONPATH=src $(UV) run --isolated --locked --with-requirements docs/requirements.lock sphinx-build -W --keep-going -E -a -b html docs docs/_build/html

docs: docs-generated
	rm -rf docs/_build/html
	PYTHONPATH=src $(UV) run --isolated --locked --with-requirements docs/requirements.lock sphinx-build -b html docs docs/_build/html

docs-linkcheck:
	rm -rf docs/_build/linkcheck
	PYTHONPATH=src $(UV) run --isolated --locked --with-requirements docs/requirements.lock sphinx-build -W --keep-going -E -a -b linkcheck docs docs/_build/linkcheck

docs-lock:
	$(UV) pip compile --python-version 3.12 --universal --output-file docs/requirements.lock docs/requirements.in

service-check:
	$(RUN) scripts/check_service_conventions.py

siren-spec:
	$(RUN) scripts/siren_spec.py

verify-fast:
	$(RUN) -m ruff check .
	$(RUN) -m pytest -m "not complete"

verify: docs-check service-check siren-spec
	$(RUN) -m ruff check .
	$(RUN) -m pytest

package-check:
	rm -rf dist/quality
	mkdir -p dist/quality
	$(RUN) -m build --wheel --sdist --outdir dist/quality
	$(RUN) -m twine check dist/quality/*

quality: verify package-check
