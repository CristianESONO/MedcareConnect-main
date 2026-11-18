#!/usr/bin/env bash
# Mise à jour MedCare Connect en production (code + static + migrations).
# Usage (sur le serveur, depuis /usr/local/etc/MedcareConnect) :
#   bash backend/scripts/deploy_server_update.sh
# Pour réinitialiser les mots de passe structures, définir MEDCARE_STRUCTURE_RESET_PASSWORD.
set -euo pipefail

APP_DIR="${APP_DIR:-/usr/local/etc/MedcareConnect}"
SERVICE_NAME="${SERVICE_NAME:-medcareconnect}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"

cd "$APP_DIR"

if [[ -d venv/bin ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
elif [[ -d .venv/bin ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PY="${PY:-python3}"
if command -v python >/dev/null 2>&1; then
  PY=python
fi

echo "==> Git pull ($GIT_REMOTE/$GIT_BRANCH)"
git fetch "$GIT_REMOTE"
git pull "$GIT_REMOTE" "$GIT_BRANCH"

echo "==> Dépendances Python"
pip install -r backend/requirements.txt -q

echo "==> Migrations"
$PY backend/manage.py migrate --noinput

echo "==> Fichiers statiques"
$PY backend/manage.py collectstatic --noinput

echo "==> Référentiel catalogue (piliers / actes)"
$PY backend/manage.py shell -c "from healthcare.data.catalog_loader import load_pillars_from_docs; load_pillars_from_docs()"

if [[ -n "${MEDCARE_STRUCTURE_RESET_PASSWORD:-}" ]]; then
  echo "==> Mise à jour des mots de passe structures"
  $PY backend/manage.py reset_structure_passwords --password "$MEDCARE_STRUCTURE_RESET_PASSWORD"
else
  echo "==> Mise à jour des mots de passe structures ignorée (MEDCARE_STRUCTURE_RESET_PASSWORD non défini)"
fi

echo "==> Redémarrage Gunicorn ($SERVICE_NAME)"
systemctl restart "$SERVICE_NAME"
systemctl is-active --quiet "$SERVICE_NAME"
echo "==> OK — service actif."
