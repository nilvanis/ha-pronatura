#!/bin/bash

# Script to run tests in a Docker container similar to GitHub Actions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Running tests in Docker (like CI)"

# Default Python version (can be overridden with environment variable)
PYTHON_VERSION=${PYTHON_VERSION:-3.13}

echo "Using Python ${PYTHON_VERSION}"
echo ""

# Run tests in a Docker container similar to GitHub Actions
docker run --rm \
    -v "$(pwd):/workspace" \
    -w /workspace \
    -e "HOST_UID=$(id -u)" \
    -e "HOST_GID=$(id -g)" \
    python:${PYTHON_VERSION}-slim \
    bash -c "
        set -e
        echo 'Installing system dependencies...'
        apt-get update -qq
        apt-get install -y -qq git gcc python3-dev > /dev/null 2>&1

        echo 'Upgrading pip...'
        python -m pip install --upgrade pip -q

        echo 'Installing project dependencies...'
        # Copy project to temp location to avoid creating build artifacts in mounted volume
        mkdir -p /tmp/build
        cp -r /workspace/* /tmp/build/
        cd /tmp/build
        pip install --no-cache-dir '.[test]' -q
        cd /workspace

        echo 'Installing ruff...'
        pip install ruff -q

        echo ''
        echo 'Running ruff linter'
        ruff check .

        echo ''
        echo 'Running ruff formatter check'
        ruff format --check .

        echo ''
        echo 'Running pytest with coverage'
        pytest tests/ -v --cov=custom_components/pronatura --cov-report=term-missing --cov-report=xml

        # Fix permissions on generated files
        if [ -n \"\$HOST_UID\" ] && [ -n \"\$HOST_GID\" ]; then
            chown -R \$HOST_UID:\$HOST_GID /workspace/htmlcov /workspace/coverage.xml /workspace/.coverage 2>/dev/null || true
        fi
    "

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}All checks passed in Docker!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}Some checks failed in Docker.${NC}"
    exit 1
fi
