# Development Scripts

This directory contains helper scripts for running CI checks locally.

## Available Scripts

### `run_checks.sh`

Runs all checks that are performed in GitHub Actions CI pipeline:

- **Ruff linting** - Code quality checks
- **Ruff formatting** - Code formatting validation
- **Pytest** - Unit tests with coverage reporting
- **Hassfest** - Home Assistant integration validation

**Usage:**

```bash
./scripts/run_checks.sh
```

This is useful to run before pushing to ensure your changes will pass CI.

### `run_hassfest.sh`

Runs only the hassfest validation for the pronatura custom component.

**Usage:**

```bash
./scripts/run_hassfest.sh
```

This is faster than the full check suite when you only need to validate the integration manifest and translations.

### `run_tests_docker.sh`

Runs all checks (linting, formatting, tests) in a Docker container using the same Python environment as GitHub Actions. This ensures your local tests match the CI environment exactly.

**Usage:**

```bash
./scripts/run_tests_docker.sh
```

**Advanced usage with different Python versions:**

```bash
PYTHON_VERSION=3.12 ./scripts/run_tests_docker.sh
```

This script:

- Uses the official Python Docker image (default: 3.13-slim)
- Installs dependencies fresh each time (no cache issues)
- Runs ruff linting, formatting, and pytest
- Matches the GitHub Actions CI environment closely

## Requirements

- Python 3.12 or 3.13
- Docker (for hassfest validation)
- Virtual environment set up at `.venv/` with dependencies installed:

  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install ".[test]"
  pip install ruff
  ```

The scripts will automatically activate the `.venv` virtual environment if it exists.
