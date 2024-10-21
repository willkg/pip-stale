@_default:
    just --list

# Build a development environment
devenv:
    uv sync --extra dev --refresh --upgrade

# Wipe devenv and build artifacts
clean:
    rm -rf .venv uv.lock
    rm -rf build dist pip_stale.egg-info .tox .pytest_cache .mypy_cache
    find pip_stale/ -name __pycache__ | xargs rm -rf
    find pip_stale/ -name '*.pyc' | xargs rm -rf

# Run tests
test: devenv
    tox

# Generate test data
generatetestdata: devenv
    -rm tests/pypi_output.yaml
    tox exec -e py39 -- python tests/create_data.py
    ls -l tests/pypi_output.yaml

# Format files
format:
    tox exec -e py39-lint -- ruff format

# Lint files
lint:
    tox -e py39-lint

# Generate docs
docs: devenv
    tox exec -e py39-lint -- python -m cogapp -r README.rst

# Build release packages
build: devenv
    rm -rf build/ dist/
    uv run python -m build
    uv run twine check dist/*
    uv run check-manifest
