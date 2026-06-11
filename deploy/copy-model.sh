#!/usr/bin/env bash
# Copy the trained model artifacts to the VPS via scp.
# Run this from your local machine after deploy.sh has run at least once.
#
# Usage: ./deploy/copy-model.sh user@vps-host
# Example: ./deploy/copy-model.sh foodqcheck@foodqcheck.drenzzz.dev

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <ssh-target>" >&2
  echo "Example: $0 foodqcheck@foodqcheck.drenzzz.dev" >&2
  exit 1
fi

TARGET="$1"
REMOTE_DIR="/opt/foodqcheck/ml/model/umkm_food_quality_v1"
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
ssh "${TARGET}" "sudo mkdir -p ${REMOTE_DIR} && sudo chown -R foodqcheck:foodqcheck /opt/foodqcheck/ml"

echo "=== Copying model.keras and class_indices.json"
scp "${LOCAL_DIR}/model.keras" "${LOCAL_DIR}/class_indices.json" "${TARGET}:${REMOTE_DIR}/"

echo "=== Fixing ownership"
ssh "${TARGET}" "sudo chown -R foodqcheck:foodqcheck ${REMOTE_DIR}"

echo "=== Restarting service so it picks up the new model"
ssh "${TARGET}" "sudo systemctl restart foodqcheck.service"

echo "=== Health check"
ssh "${TARGET}" "sleep 2 && curl --silent http://127.0.0.1:8000/health"

echo
echo "[OK] Model deployed"
