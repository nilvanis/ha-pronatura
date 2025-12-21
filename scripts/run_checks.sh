#!/bin/bash

# Script to run all checks that are performed in GitHub Actions
# This includes: ruff linting, ruff formatting, pytest, and hassfest validation

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "Warning: .venv not found. Make sure dependencies are installed."
fi

echo "Running all CI checks locally"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any checks fail
FAILED=0

# Function to handle check results
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1 passed${NC}"
    else
        echo -e "${RED}✗ $1 failed${NC}"
        FAILED=1
    fi
}

# 1. Ruff linting
ruff check .
check_result "Ruff linting"

# 2. Ruff formatting check
ruff format --check .
check_result "Ruff formatting"

# 3. Run tests with coverage
pytest tests/ -v --cov=custom_components/pronatura --cov-report=term-missing --cov-report=xml
check_result "Pytest"

# 4. Hassfest validation
echo "Running hassfest validation"
if command -v docker &> /dev/null; then
    docker run --rm -v "$(pwd)/custom_components/pronatura:/github/workspace/custom_components/pronatura" ghcr.io/home-assistant/hassfest:latest
    check_result "Hassfest"
else
    echo -e "${YELLOW}⚠ Docker not found, skipping hassfest validation${NC}"
fi

# Summary
echo ""
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Please review the output above.${NC}"
    exit 1
fi
