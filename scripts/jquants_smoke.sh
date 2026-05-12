#!/usr/bin/env bash
# dry-run | live smoke for jquants-watchlist-bars (live requires confirmation).
# Loads whitelisted J-Quants keys via scripts/load_jquants_env.py (no shell sourcing of .env file).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

MODE="${1:-}"
DATE="${2:-}"
LIMIT="${3:-}"

usage() {
  cat >&2 <<'U'
usage: jquants_smoke.sh dry-run DATE LIMIT
       jquants_smoke.sh live DATE LIMIT    (requires CONFIRM_LIVE_HTTP=YES)

Examples:
  DATE=2024-02-19 LIMIT=3 PYTHON=.venv/bin/python bash scripts/jquants_smoke.sh dry-run 2024-02-19 3
  CONFIRM_LIVE_HTTP=YES DATE=2024-02-19 LIMIT=3 PYTHON=.venv/bin/python bash scripts/jquants_smoke.sh live 2024-02-19 3
U
}

if [[ -z "${MODE}" ]] || [[ -z "${DATE}" ]] || [[ -z "${LIMIT}" ]]; then
  usage
  exit 1
fi

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

case "${MODE}" in
  dry-run)
    echo "=== jquants-smoke dry-run (DATE=${DATE} LIMIT=${LIMIT}) ==="
    exec "${PYTHON}" "${ROOT}/scripts/load_jquants_env.py" run --env-file "${ROOT}/.env" -- \
      "${PYTHON}" -m invis_alpha_os.cli.main debug jquants-watchlist-bars \
      --date "${DATE}" --limit "${LIMIT}" --save-summary
    ;;
  live)
    if [[ "${CONFIRM_LIVE_HTTP:-}" != "YES" ]]; then
      echo "ERROR: live HTTP blocked. Export CONFIRM_LIVE_HTTP=YES to proceed." >&2
      exit 1
    fi
    echo "=== jquants-smoke LIVE (DATE=${DATE} LIMIT=${LIMIT}) ==="
    exec "${PYTHON}" "${ROOT}/scripts/load_jquants_env.py" run --env-file "${ROOT}/.env" \
      --set JQUANTS_ALLOW_LIVE_HTTP=true -- \
      "${PYTHON}" -m invis_alpha_os.cli.main debug jquants-watchlist-bars \
      --date "${DATE}" --limit "${LIMIT}" --live --save-summary
    ;;
  *)
    usage
    exit 1
    ;;
esac
