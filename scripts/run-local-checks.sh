#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ "${VIRTUAL_ENV:-}" == "" ]]; then
  echo "warning: no active virtualenv detected (recommended: python3.11 -m venv .venv && source .venv/bin/activate)"
fi

python -V

echo "Running local-service tests..."
PYTHONPATH=apps/local-service/src python -m unittest discover -s apps/local-service/tests -t .

echo "Running desktop tests..."
PYTHONPATH=apps/local-service/src:apps/desktop/src python -m unittest discover -s apps/desktop/tests -t .

echo "All local checks passed."
