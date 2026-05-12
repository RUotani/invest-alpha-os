#!/usr/bin/env bash
# Live bulk cache fill: requires CONFIRM_LIVE_HTTP=YES, FROM, TO.
# LIMIT is required when CODES is unset; when CODES is set, LIMIT is optional (slices code list).
# Matches CLI: debug jquants-watchlist-bars-cache requires CONFIRM for any --live.
# Sets JQUANTS_ALLOW_LIVE_HTTP=true via load_jquants_env --set.
# Optional JQ_OPS_OUTPUT_DIR overrides outputs/ops (tests / tooling).
#
# pytest-only hooks — require ALLOW_TEST_JQ_STUBS=YES (prevents stray env spoofing gates):
# - TEST_JQ_LIVE_STUB_PAYLOAD: JSON file copied as CLI stdout (+ TEST_JQ_LIVE_CLI_EXIT, default 0).
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
if [[ -z "${CODES:-}" && -z "${LIMIT:-}" ]]; then
  echo "jq-cache-live: LIMIT is required when CODES is unset" >&2
  exit 1
fi

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

OUT="$(mktemp)"
cleanup() { rm -f "${OUT}"; }
trap cleanup EXIT

CLI_ARGS=(
  "${PYTHON}" -m invis_alpha_os.cli.main debug jquants-watchlist-bars-cache
  --from-date "${FROM}" --to-date "${TO}" --live --write-cache
)

if [[ -n "${CODES:-}" ]]; then
  CLI_ARGS+=(--codes "${CODES}")
fi
if [[ -n "${LIMIT:-}" ]]; then
  CLI_ARGS+=(--limit "${LIMIT}")
fi

OPS_DIR="${JQ_OPS_OUTPUT_DIR:-${ROOT}/outputs/ops}"

if [[ -n "${TEST_JQ_LIVE_STUB_PAYLOAD:-}" ]]; then
  if [[ "${ALLOW_TEST_JQ_STUBS:-}" != "YES" ]]; then
    echo "jq-cache-live: TEST_JQ_LIVE_STUB_PAYLOAD requires ALLOW_TEST_JQ_STUBS=YES (test-only isolation)" >&2
    exit 2
  fi
  if [[ ! -r "${TEST_JQ_LIVE_STUB_PAYLOAD}" ]]; then
    echo "jq-cache-live: TEST_JQ_LIVE_STUB_PAYLOAD not readable" >&2
    exit 2
  fi
  CLI_EXIT="${TEST_JQ_LIVE_CLI_EXIT:-0}"
  cp "${TEST_JQ_LIVE_STUB_PAYLOAD}" "${OUT}"
else
  set +e
  "${PYTHON}" "${ROOT}/scripts/load_jquants_env.py" run \
    --env-file "${ROOT}/.env" \
    --set JQUANTS_ALLOW_LIVE_HTTP=true \
    -- \
    "${CLI_ARGS[@]}" > "${OUT}"
  CLI_EXIT=$?
  set -e
fi

mkdir -p "${OPS_DIR}"

if [[ "${CLI_EXIT}" -eq 0 || "${CLI_EXIT}" -eq 1 ]]; then
  set +e
  "${PYTHON}" "${ROOT}/scripts/ops_write_json.py" \
    --mode jquants_watchlist_cache_live \
    --payload-file "${OUT}" \
    --output-dir "${OPS_DIR}"
  OPS_EC=$?
  set -e
  if [[ "${OPS_EC}" -ne 0 ]]; then
    echo "jq-cache-live: ops_write_json failed (fatal, exit=${OPS_EC})" >&2
    exit "${OPS_EC}"
  fi
else
  echo "jq-cache-live: skipping ops JSON (CLI exit ${CLI_EXIT})" >&2
fi

exit "${CLI_EXIT}"
