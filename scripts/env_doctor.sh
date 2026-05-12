#!/usr/bin/env bash
# Show J-Quants-related env *presence* only (never values or full .env).
# Reads .env via scripts/load_jquants_env.py (no source/eval — Hotfix C).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

echo "=== env-doctor ==="
echo "repo: ${ROOT}"
if [[ -f "${ROOT}/.env" ]]; then
  echo ".env file: present (contents not displayed)"
else
  echo ".env file: absent"
fi
echo "---"

"${PYTHON}" "${ROOT}/scripts/load_jquants_env.py" doctor --env-file "${ROOT}/.env"

echo "=== end env-doctor ==="
