#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PROJECT_ROOT}/.venv-ml/bin/python"
NVIDIA_SITE_ROOT="${PROJECT_ROOT}/.venv-ml/lib/python3.11/site-packages/nvidia"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  printf 'Missing ML Python interpreter: %s\n' "${PYTHON_BIN}" >&2
  exit 1
fi

if [[ ! -d "${NVIDIA_SITE_ROOT}" ]]; then
  printf 'Missing NVIDIA runtime directory: %s\n' "${NVIDIA_SITE_ROOT}" >&2
  exit 1
fi

LIBRARY_PATHS=()
while IFS= read -r -d '' lib_dir; do
  LIBRARY_PATHS+=("${lib_dir}")
done < <(find "${NVIDIA_SITE_ROOT}" -mindepth 2 -maxdepth 2 -type d -name lib -print0 | sort -z)

if [[ ${#LIBRARY_PATHS[@]} -eq 0 ]]; then
  printf 'No NVIDIA library directories were found under: %s\n' "${NVIDIA_SITE_ROOT}" >&2
  exit 1
fi

EXTRA_LIBRARY_PATH="$(IFS=:; printf '%s' "${LIBRARY_PATHS[*]}")"
export LD_LIBRARY_PATH="${EXTRA_LIBRARY_PATH}:/usr/lib:/opt/cuda/lib64:${LD_LIBRARY_PATH:-}"

exec "${PYTHON_BIN}" "$@"
