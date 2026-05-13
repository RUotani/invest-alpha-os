#!/usr/bin/env bash
# Main R0.5 — verification sweep + agent handoff under outputs/ops (gitignored, never committed).
#
# No market-data live HTTP. Daily momentum step uses scripts/agent_daily_momentum_check_no_env.sh
# (``daily`` CLI with process env only — does not read ROOT/.env via load_jquants_env). Optional
# read-only ``gh`` metadata in post-push-check when the GitHub CLI is installed.

set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x "${ROOT}/.venv/bin/python" ]]; then
    PYTHON="${ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

OPS_DIR="${AGENT_HANDOFF_OPS_DIR:-${ROOT}/outputs/ops}"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/agent_final_chk.XXXXXX")"
cleanup() { rm -rf "${WORKDIR}"; }
trap cleanup EXIT

mkdir -p "${OPS_DIR}"

overall_ec=0

echo "=== agent-final-check: pytest ==="
set +e
"${PYTHON}" -m pytest -q >"${WORKDIR}/pytest.out" 2>&1
pytest_ec=$?
set -e
if [[ "${pytest_ec}" != 0 ]]; then
  overall_ec=1
fi
cat "${WORKDIR}/pytest.out"

echo "=== agent-final-check: signals-cache-only ==="
set +e
PYTHON="${PYTHON}" make -s signals-cache-only >"${WORKDIR}/signals.out" 2>&1
signals_ec=$?
set -e
if [[ "${signals_ec}" != 0 ]]; then
  overall_ec=1
fi
cat "${WORKDIR}/signals.out"

echo "=== agent-final-check: daily momentum verification (agent; no .env file merge, no live HTTP) ==="
set +e
PYTHON="${PYTHON}" bash "${ROOT}/scripts/agent_daily_momentum_check_no_env.sh" >"${WORKDIR}/daily_momentum.out" 2>&1
daily_ec=$?
set -e
if [[ "${daily_ec}" != 0 ]]; then
  overall_ec=1
fi
cat "${WORKDIR}/daily_momentum.out"

echo "=== agent-final-check: investment-os-coverage ==="
set +e
PYTHON="${PYTHON}" make -s investment-os-coverage >"${WORKDIR}/coverage_doc.out" 2>&1
cov_ec=$?
set -e
if [[ "${cov_ec}" != 0 ]]; then
  overall_ec=1
fi
cat "${WORKDIR}/coverage_doc.out"

echo "=== agent-final-check: post-push-check (optional gh; read-only) ==="
set +e
bash "${ROOT}/scripts/post_push_check.sh" >"${WORKDIR}/post_push.out" 2>&1
set -e
cat "${WORKDIR}/post_push.out"

ppc="unknown"
if grep -Fq "warning: gh CLI not found" "${WORKDIR}/post_push.out" 2>/dev/null; then
  ppc="skipped_no_gh"
elif grep -Fq "warning: gh run list failed" "${WORKDIR}/post_push.out" 2>/dev/null; then
  ppc="degraded"
elif grep -Fq "Latest run:" "${WORKDIR}/post_push.out" 2>/dev/null; then
  ppc="ok"
fi

echo "=== agent-final-check: git status ==="
set +e
git -C "${ROOT}" status --short >"${WORKDIR}/git_status.out" 2>&1
gst=$?
set -e
git_lines="$(cat "${WORKDIR}/git_status.out")"
if [[ "${gst}" != 0 ]]; then
  overall_ec=1
fi
echo "${git_lines}"

handoff_payload="${WORKDIR}/handoff_payload.json"
"${PYTHON}" "${ROOT}/scripts/agent_handoff_summary.py" merge-logs \
  --pytest-exit-code "${pytest_ec}" \
  --pytest-log "${WORKDIR}/pytest.out" \
  --signals-exit-code "${signals_ec}" \
  --signals-log "${WORKDIR}/signals.out" \
  --daily-momentum-exit-code "${daily_ec}" \
  --investment-log "${WORKDIR}/coverage_doc.out" \
  --investment-exit-code "${cov_ec}" \
  --post-push-log "${WORKDIR}/post_push.out" \
  --post-push-classification "${ppc}" \
  --git-status-log "${WORKDIR}/git_status.out" \
  --out-json "${handoff_payload}"

"${PYTHON}" "${ROOT}/scripts/agent_handoff_summary.py" write \
  --from-json "${handoff_payload}" \
  --ops-dir "${OPS_DIR}"

echo "=== agent-final-check: wrote ${OPS_DIR}/latest_agent_handoff.{json,md}"

exit "${overall_ec}"
