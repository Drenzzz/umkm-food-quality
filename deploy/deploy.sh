#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_USER="foodqcheck"
SERVICE_NAME="foodqcheck"
BRANCH="${1:-main}"

cd "${APP_DIR}"

if [[ ! -f ".env" ]]; then
  echo "[FAIL] .env not found in ${APP_DIR}."
  echo "       Copy deploy/.env.production to .env and fill in real secrets first."
  exit 1
fi

echo "=== 1/7 Pull latest source from ${BRANCH}"
sudo -u "${APP_USER}" git fetch --all --prune
sudo -u "${APP_USER}" git reset --hard "origin/${BRANCH}"

echo "=== 2/7 Update Python venv"
if [[ ! -d ".venv" ]]; then
  sudo -u "${APP_USER}" python3.11 -m venv .venv
fi
sudo -u "${APP_USER}" .venv/bin/pip install --upgrade pip wheel
sudo -u "${APP_USER}" .venv/bin/pip install -r requirements-backend.txt

echo "=== 3/7 Apply database migrations"
sudo -u "${APP_USER}" .venv/bin/alembic upgrade head

echo "=== 4/7 Ensure model files are present"
if [[ ! -f "ml/model/umkm_food_quality_v1/model.keras" ]]; then
  echo "[WARN] model.keras not found. Run deploy/copy-model.sh to upload it."
  echo "       The service will still start, but /detect will fail until the model exists."
fi
if [[ ! -f "ml/model/umkm_food_quality_v1/class_indices.json" ]]; then
  echo "[WARN] class_indices.json not found. Run deploy/copy-model.sh to upload it."
fi

echo "=== 5/7 Ensure service unit is installed"
if [[ ! -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
  cp deploy/foodqcheck.service /etc/systemd/system/${SERVICE_NAME}.service
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}.service"
fi

echo "=== 6/7 Reload systemd and restart service"
systemctl daemon-reload
systemctl restart "${SERVICE_NAME}.service"

echo "=== 7/7 Health check"
sleep 2
if curl --fail --silent --max-time 5 http://127.0.0.1:8000/health >/dev/null; then
  echo "[OK] Backend health check passed"
  curl --silent http://127.0.0.1:8000/health
else
  echo "[FAIL] Backend health check failed. Check logs:"
  echo "       journalctl -u ${SERVICE_NAME} -n 100 --no-pager"
  exit 1
fi
