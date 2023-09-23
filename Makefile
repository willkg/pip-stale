DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Available rules:"
	@fgrep -h "##" Makefile | fgrep -v fgrep | sed 's/\(.*\):.*##/\1:  /'

.PHONY: test
test:  ## Run tests and linting
	tox

.PHONY: lint
lint:  ## Lint and black reformat files
	black pip_stale.py
	tox -e py38-lint

.PHONY: clean
clean:  ## Clean build artifacts
	rm -rf build dist pip_stale.egg-info .tox .pytest_cache .mypy_cache
	find __pycache__ | xargs rm -rf
	find -name '*.pyc' | xargs rm -rf

.PHONY: docs
docs:  ## Runs cog
	python -m cogapp -r README.rst
