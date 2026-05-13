#!/usr/bin/env bash
# Preview → live cache (writes outputs/ops/*.json) → optional downstream only on verdict.
# Env: FROM, TO, CONFIRM_LIVE_HTTP=YES. Optional: LIMIT, CODES, ALLOW_PARTIAL_CACHE, PYTHON,
# optional JQ_OPS_OUTPUT_DIR overrides outputs/ops.
#
# pytest-only stubs — require ALLOW_TEST_JQ_STUBS=YES:
# - TEST_JQ_REFRESH_GATE_STUB: synthetic ops JSON (writes fixtures instead of preview/live).
# - TEST_JQ_REFRESH_SKIP_DAILY=1 with ALLOW_TEST_JQ_STUBS skips daily-momentum-check in tests only.
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

export PYTHON

if [[ -z "${FROM:-}" || -z "${TO:-}" ]]; then
  echo "jq-refresh-workflow: FROM and TO are required" >&2
  exit 1
fi
if [[ "${CONFIRM_LIVE_HTTP:-}" != "YES" ]]; then
  echo "jq-refresh-workflow: CONFIRM_LIVE_HTTP=YES is required for live cache step" >&2
  exit 2
fi
if [[ -z "${CODES:-}" && -z "${LIMIT:-}" ]]; then
  echo "jq-refresh-workflow: set LIMIT or CODES" >&2
  exit 1
fi

OPS_DIR="${JQ_OPS_OUTPUT_DIR:-${ROOT}/outputs/ops}"

"${PYTHON}" "${ROOT}/scripts/jq_ops_workflow_gate.py" prepare --ops-dir "${OPS_DIR}"

if [[ "${TEST_JQ_REFRESH_GATE_STUB:-}" != "" ]]; then
  if [[ "${ALLOW_TEST_JQ_STUBS:-}" != "YES" ]]; then
    echo "jq-refresh-workflow: TEST_JQ_REFRESH_GATE_STUB requires ALLOW_TEST_JQ_STUBS=YES (test-only)" >&2
    exit 2
  fi
  WTF_CODES=()
  if [[ -n "${CODES:-}" ]]; then
    WTF_CODES=(--codes "${CODES}")
  fi
  "${PYTHON}" "${ROOT}/scripts/jq_ops_workflow_gate.py" write-test-fixture \
    --ops-dir "${OPS_DIR}" \
    --fixture "${TEST_JQ_REFRESH_GATE_STUB}" \
    --from-date "${FROM}" \
    --to-date "${TO}" \
    "${WTF_CODES[@]}"
  LIVE_EC="${TEST_JQ_REFRESH_LIVE_EXIT:-0}"
else
  PREVIEW_EXTRA=()
  [[ -n "${LIMIT:-}" ]] && PREVIEW_EXTRA+=(LIMIT="$LIMIT")
  [[ -n "${CODES:-}" ]] && PREVIEW_EXTRA+=(CODES="$CODES")

  make jq-cache-preview FROM="$FROM" TO="$TO" "${PREVIEW_EXTRA[@]}" PYTHON="$PYTHON"

  LIVE_EXTRA=()
  [[ -n "${LIMIT:-}" ]] && LIVE_EXTRA+=(LIMIT="$LIMIT")
  [[ -n "${CODES:-}" ]] && LIVE_EXTRA+=(CODES="$CODES")

  set +e
  make jq-cache-live FROM="$FROM" TO="$TO" CONFIRM_LIVE_HTTP="$CONFIRM_LIVE_HTTP" "${LIVE_EXTRA[@]}" PYTHON="$PYTHON"
  LIVE_EC=$?
  set -e
fi

SUM_OPS="${OPS_DIR}/latest_ops_summary.json"
VD_OPS="${OPS_DIR}/latest_verdict.json"
if [[ -f "${SUM_OPS}" ]] && [[ -f "${VD_OPS}" ]]; then
  "${PYTHON}" "${ROOT}/scripts/jq_ops_workflow_gate.py" print-live-ops-human --ops-dir "${OPS_DIR}" >&2 || true
fi

VAL_CODES=()
if [[ -n "${CODES:-}" ]]; then
  VAL_CODES=(--codes "${CODES}")
fi

"${PYTHON}" "${ROOT}/scripts/jq_ops_workflow_gate.py" validate \
  --ops-dir "${OPS_DIR}" \
  --from-date "${FROM}" \
  --to-date "${TO}" \
  "${VAL_CODES[@]}"
VAL_EC=$?
if [[ "${VAL_EC}" -ne 0 ]]; then
  exit "${VAL_EC}"
fi

VERDICT_JSON="${OPS_DIR}/latest_verdict.json"
verdict="$("${PYTHON}" -c "import json,sys; print(json.load(open(sys.argv[1],encoding='utf-8'))['verdict'])" "${VERDICT_JSON}")"

run_next=0
if [[ "${verdict}" == "pass" ]]; then
  run_next=1
elif [[ "${verdict}" == "partial_success" ]] && [[ "${ALLOW_PARTIAL_CACHE:-}" == "true" ]]; then
  run_next=1
fi

if [[ "${run_next}" -eq 1 ]]; then
  if [[ -n "${LIMIT:-}" ]]; then
    make signals-cache-only PYTHON="$PYTHON" LIMIT="$LIMIT"
  else
    make signals-cache-only PYTHON="$PYTHON"
  fi
  if [[ "${TEST_JQ_REFRESH_SKIP_DAILY:-}" == "1" ]]; then
    if [[ "${ALLOW_TEST_JQ_STUBS:-}" != "YES" ]]; then
      echo "jq-refresh-workflow: TEST_JQ_REFRESH_SKIP_DAILY requires ALLOW_TEST_JQ_STUBS=YES (test-only)" >&2
      exit 2
    fi
    echo "jq-refresh-workflow: skipping daily-momentum-check (TEST_JQ_REFRESH_SKIP_DAILY=1)"
  else
    PYTHON="$PYTHON" bash scripts/daily_momentum_check.sh
  fi
  exit 0
fi

echo "jq-refresh-workflow: stopping downstream (verdict=${verdict})" >&2
if [[ "${LIVE_EC}" -ne 0 ]]; then
  exit "${LIVE_EC}"
fi
exit 1
