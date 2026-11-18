#!/usr/bin/env bash
# Tests parcours QA (pytest-django, dossier qa_tests/).
set -euo pipefail
cd "$(dirname "$0")/.."
export DATABASE_URL="${DATABASE_URL:-}"
exec .venv/bin/python -m pytest qa_tests "$@"
