#!/usr/bin/env bash
set -euo pipefail

# Docker Compose deployment script.
# Usage: ./deploy/deploy.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${APP_DIR}"

if [[ ! -f "deploy/env.production" ]]; then
  echo "[FAIL] deploy/env.production not found."
  echo "       Copy deploy/env.docker.template to deploy/env.production and fill in real secrets first."
  exit 1
fi

echo "=== 1/3 Building and starting Docker containers"
docker compose -f deploy/docker-compose.yml up -d --build

echo "=== 2/3 Waiting for containers to be healthy"
sleep 5

echo "=== 3/3 Health check"
if curl --fail --silent --max-time 5 http://localhost/api/health >/dev/null; then
  echo "[OK] Backend health check passed"
  curl --silent http://localhost/api/health
else
  echo "[FAIL] Backend health check failed. Check logs:"
  echo "       docker compose -f deploy/docker-compose.yml logs -f api"
  exit 1
fi
