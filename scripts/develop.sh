#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$PROJECT_DIR/config"
COMPONENT_LINK="$CONFIG_DIR/custom_components/pronatura"

mkdir -p "$CONFIG_DIR/custom_components"
if [[ ! -e "$CONFIG_DIR/configuration.yaml" ]]; then
    cp "$PROJECT_DIR/.devcontainer/configuration.yaml" "$CONFIG_DIR/configuration.yaml"
fi

if [[ -e "$COMPONENT_LINK" && ! -L "$COMPONENT_LINK" ]]; then
    echo "Cannot link ProNatura: $COMPONENT_LINK already exists and is not a symlink." >&2
    exit 1
fi
ln -sfn "$PROJECT_DIR/custom_components/pronatura" "$COMPONENT_LINK"

if [[ "${1:-}" == "--prepare" ]]; then
    exit 0
fi

cd "$PROJECT_DIR"
PYTHON="$PROJECT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
    PYTHON=python3
fi
exec "$PYTHON" -m homeassistant --config "$CONFIG_DIR" "$@"
