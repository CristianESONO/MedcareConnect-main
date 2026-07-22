#!/usr/bin/env bash
# Tests unitaires Django (SQLite en mémoire si DATABASE_URL non défini).
set -euo pipefail
cd "$(dirname "$0")/.."
export DATABASE_URL="${DATABASE_URL:-}"
exec .venv/bin/python manage.py test notifications.tests healthcare.tests cart.tests -v 2 "$@"
