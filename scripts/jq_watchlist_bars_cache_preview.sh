#!/usr/bin/env bash
# Dry-run preview for debug jquants-watchlist-bars-cache (no HTTP, no cache write).
# Env: FROM, TO required; LIMIT optional. PYTHON optional.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -z "${FROM:-}" ]]; then
  echo "jq-cache-preview: FROM is required (YYYY-MM-DD)" >&2
  exit 1
fi
if [[ -z "${TO:-}" ]]; then
  echo "jq-cache-preview: TO is required (YYYY-MM-DD)" >&2
  exit 1
fi

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

LIMIT_ARGS=()
if [[ -n "${LIMIT:-}" ]]; then
  LIMIT_ARGS=(--limit "${LIMIT}")
fi

exec "${PYTHON}" "${ROOT}/scripts/load_jquants_env.py" run --env-file "${ROOT}/.env" -- \
  "${PYTHON}" -m invis_alpha_os.cli.main debug jquants-watchlist-bars-cache \
  --from-date "${FROM}" --to-date "${TO}" "${LIMIT_ARGS[@]}"
