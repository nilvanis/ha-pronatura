#!/bin/bash

# Script to run hassfest validation for the pronatura custom component

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Running hassfest validation for pronatura custom component..."
echo ""

docker run --rm \
    -v "$(pwd)/custom_components/pronatura:/github/workspace/custom_components/pronatura" \
    ghcr.io/home-assistant/hassfest:latest
