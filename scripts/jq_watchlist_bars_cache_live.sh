#!/usr/bin/env bash
# Live bulk cache fill: requires CONFIRM_LIVE_HTTP=YES, FROM, TO, LIMIT.
# Matches CLI: debug jquants-watchlist-bars-cache requires CONFIRM for any --live (not only --write-cache).
# Sets JQUANTS_ALLOW_LIVE_HTTP=true via load_jquants_env --set (inherit CONFIRM from environment).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ "${CONFIRM_LIVE_HTTP:-}" != "YES" ]]; then
  echo "jq-cache-live: CONFIRM_LIVE_HTTP=YES is required for bulk live HTTP" >&2
  exit 2
fi
if [[ -z "${FROM:-}" ]]; then
  echo "jq-cache-live: FROM is required" >&2
  exit 1
fi
if [[ -z "${TO:-}" ]]; then
  echo "jq-cache-live: TO is required" >&2
  exit 1
fi
if [[ -z "${LIMIT:-}" ]]; then
  echo "jq-cache-live: LIMIT is required" >&2
  exit 1
fi

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

exec "${PYTHON}" "${ROOT}/scripts/load_jquants_env.py" run \
  --env-file "${ROOT}/.env" \
  --set JQUANTS_ALLOW_LIVE_HTTP=true \
  -- \
  "${PYTHON}" -m invis_alpha_os.cli.main debug jquants-watchlist-bars-cache \
  --from-date "${FROM}" --to-date "${TO}" --limit "${LIMIT}" --live --write-cache
