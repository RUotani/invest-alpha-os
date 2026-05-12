#!/usr/bin/env bash
# dry-run | live smoke for jquants-watchlist-bars (live requires confirmation).
# Never prints secrets or whole .env.
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

load_env_quiet() {
  if [[ -f "${ROOT}/.env" ]]; then
    echo "(loading .env; values not displayed)"
    # shellcheck disable=SC1091
    set -a
    source "${ROOT}/.env"
    set +a
  else
    echo "(no .env file at repo root)"
  fi
}

case "${MODE}" in
  dry-run)
    echo "=== jquants-smoke dry-run (DATE=${DATE} LIMIT=${LIMIT}) ==="
    exec "${PYTHON}" -m invis_alpha_os.cli.main debug jquants-watchlist-bars \
      --date "${DATE}" --limit "${LIMIT}" --save-summary
    ;;
  live)
    if [[ "${CONFIRM_LIVE_HTTP:-}" != "YES" ]]; then
      echo "ERROR: live HTTP blocked. Export CONFIRM_LIVE_HTTP=YES to proceed." >&2
      exit 1
    fi
    echo "=== jquants-smoke LIVE (DATE=${DATE} LIMIT=${LIMIT}) ==="
    load_env_quiet
    exec env JQUANTS_ALLOW_LIVE_HTTP=true "${PYTHON}" -m invis_alpha_os.cli.main debug jquants-watchlist-bars \
      --date "${DATE}" --limit "${LIMIT}" --live --save-summary
    ;;
  *)
    usage
    exit 1
    ;;
esac
