#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# A new Docker volume is owned by root; keep the venv writable by the developer.
if [[ -d .venv && ! -w .venv ]]; then
    sudo chown "$(id -u):$(id -g)" .venv
fi
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements_dev.txt
