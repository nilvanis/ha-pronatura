#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PYTHON="$PROJECT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    PYTHON=python3
fi

"$PYTHON" -m ruff check .
"$PYTHON" -m ruff format --check .
"$PYTHON" -m pytest tests "$@"
