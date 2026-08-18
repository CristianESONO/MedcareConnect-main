#!/usr/bin/env bash
# Mise à jour MedCare Connect en production (code + static + mots de passe structures).
# Usage (sur le serveur, depuis /usr/local/etc/MedcareConnect) :
#   bash scripts/deploy_server_update.sh
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
pip install -r requirements.txt -q

echo "==> Migrations"
$PY manage.py migrate --noinput

echo "==> Fichiers statiques"
$PY manage.py collectstatic --noinput

echo "==> Référentiel catalogue (piliers / actes)"
$PY manage.py shell -c "from healthcare.data.catalog_loader import load_pillars_from_docs; load_pillars_from_docs()" || true

echo "==> Mots de passe structures → medcare2024"
$PY manage.py reset_structure_passwords

echo "==> Redémarrage Gunicorn ($SERVICE_NAME)"
systemctl restart "$SERVICE_NAME"
systemctl is-active --quiet "$SERVICE_NAME"
echo "==> OK — service actif."
