#!/usr/bin/env bash
# Container entrypoint — apply migrations then exec the CMD.
set -euo pipefail

if [[ -n "${DATABASE_URL:-}" ]]; then
    echo "[entrypoint] Applying database migrations"
    alembic upgrade head || echo "[entrypoint] WARNING: migration step failed (continuing)"
fi

exec "$@"
