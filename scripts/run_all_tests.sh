#!/usr/bin/env bash
# Lance toute la batterie de tests automatisés MedCare Connect.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Django (unit + intégration) — base test jetable, détruite à la fin ==="
python3 manage.py test \
  cart.tests \
  healthcare.tests \
  messaging.tests \
  appointments.tests \
  notifications.tests \
  -v1

echo ""
echo "=== Pytest QA (parcours complets patient / structure / admin) ==="
python3 -m pytest qa_tests -q

echo ""
echo "=== Playwright (navigateur) — base .cache/e2e_playwright.sqlite3 supprimée après ==="
MEDCARE_START_SERVER=1 python3 scripts/playwright_smoke.py

echo ""
echo "Tous les tests sont passés."
