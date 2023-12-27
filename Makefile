DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Available rules:"
	@fgrep -h "##" Makefile | fgrep -v fgrep | sed 's/\(.*\):.*##/\1:  /'

.PHONY: test
test:  ## Run tests and linting
	tox

.PHONY: generatetestdata
generatetestdata:  ## Generate test data
	-rm tests/pypi_output.yaml
	tox exec -e py38 -- python tests/create_data.py
	ls -l tests/pypi_output.yaml

.PHONY: format
format:  ## Format files
	tox exec -e py38-lint -- ruff format

.PHONY: lint
lint:  ## Lint files
	tox -e py38-lint

.PHONY: clean
clean:  ## Clean build artifacts
	rm -rf build dist pip_stale.egg-info .tox .pytest_cache .mypy_cache
	find __pycache__ | xargs rm -rf
	find -name '*.pyc' | xargs rm -rf

.PHONY: docs
docs:  ## Runs cog
	tox exec -e py38 -- python -m cogapp -r README.rst
