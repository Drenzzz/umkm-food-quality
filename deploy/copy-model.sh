#!/usr/bin/env bash
# Copy the trained model artifacts to the VPS via scp.
# Run this from your local machine after deploy.sh has run at least once.
#
# Usage: ./deploy/copy-model.sh <ssh-target>
# Example: ./deploy/copy-model.sh drenzzz@165.22.102.163

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <ssh-target>" >&2
  echo "Example: $0 drenzzz@165.22.102.163" >&2
  exit 1
fi

TARGET="$1"
REMOTE_DIR="~/foodqcheck/ml/model/umkm_food_quality_v1"
LOCAL_DIR="ml/model/umkm_food_quality_v1"

if [[ ! -f "${LOCAL_DIR}/model.keras" ]]; then
  echo "[FAIL] ${LOCAL_DIR}/model.keras not found."
  echo "       Train the model first or copy it from your training environment."
  exit 1
fi

if [[ ! -f "${LOCAL_DIR}/class_indices.json" ]]; then
  echo "[FAIL] ${LOCAL_DIR}/class_indices.json not found."
  exit 1
fi

echo "=== Creating remote directory"
ssh "${TARGET}" "mkdir -p ${REMOTE_DIR}"

echo "=== Copying model files"
scp "${LOCAL_DIR}/model.keras" "${LOCAL_DIR}/class_indices.json" "${TARGET}:${REMOTE_DIR}/"

echo "=== Restarting api container so it picks up the new model"
ssh "${TARGET}" "cd ~/foodqcheck && docker compose -f deploy/docker-compose.yml restart api"

echo "=== Health check"
ssh "${TARGET}" "sleep 3 && curl --silent http://localhost/api/health"

echo
echo "[OK] Model deployed"
