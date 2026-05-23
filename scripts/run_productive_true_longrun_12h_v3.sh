#!/usr/bin/env bash
# R7.0-Ops-I11: productive 12h v3 utilization queue (early completion + notify; no auto-merge).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

export PATH="${REPO_ROOT}/.venv/bin:${PATH}"
PYTHON="${PYTHON:-${REPO_ROOT}/.venv/bin/python}"
export PYTHON

PRODUCTIVE_QUEUE="${PRODUCTIVE_QUEUE:-config/tasks/autonomous_dev_queue_productive_12h_v3.yaml}"
PROFILE_NAME="true_longrun_12h_productive_v3"
PROFILE_FILE="config/operator_dev_loop_profiles.yaml"
PRODUCTIVE_LABEL="PRODUCTIVE-LONGRUN-12H-V3"
MIN_RUNTIME_MINUTES=720
MAX_PRS=15
MAX_TASKS=72

preflight_fail() {
  echo "${PRODUCTIVE_LABEL} PREFLIGHT FAILED: $1" >&2
  echo "next action: $2" >&2
  exit 2
}

if [[ "${CONFIRM_OPERATOR_DEV_LOOP:-}" != "YES" ]]; then
  preflight_fail "CONFIRM_OPERATOR_DEV_LOOP=YES is not set" "export CONFIRM_OPERATOR_DEV_LOOP=YES"
fi
if [[ "${CONFIRM_GITHUB_PR_CREATE:-}" != "YES" ]]; then
  preflight_fail "CONFIRM_GITHUB_PR_CREATE=YES is not set" "export CONFIRM_GITHUB_PR_CREATE=YES"
fi

if [[ -n "$(git status --short)" ]]; then
  preflight_fail "working tree is dirty" "commit, stash, or discard changes before starting 12h v3 run"
fi

if pgrep -f "operator-runner dev-loop" >/dev/null 2>&1; then
  preflight_fail "another operator-runner dev-loop process is running" "stop the other dev-loop run first"
fi

if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  preflight_fail ".venv/bin/python missing" "create venv and install dependencies"
fi

if [[ -x "${REPO_ROOT}/.venv/bin/pytest" ]]; then
  if ! "${REPO_ROOT}/.venv/bin/pytest" --version >/dev/null 2>&1; then
    preflight_fail "pytest not runnable" "pip install pytest in .venv"
  fi
elif ! "${REPO_ROOT}/.venv/bin/python" -m pytest --version >/dev/null 2>&1; then
  preflight_fail "pytest not available" "fix .venv pytest"
fi

if [[ ! -f "${REPO_ROOT}/${PRODUCTIVE_QUEUE}" ]]; then
  preflight_fail "task queue not found: ${PRODUCTIVE_QUEUE}" "merge I11 PR or fix path"
fi

if [[ ! -f "${REPO_ROOT}/${PROFILE_FILE}" ]]; then
  preflight_fail "profile file not found: ${PROFILE_FILE}" "ensure operator_dev_loop_profiles.yaml exists"
fi

if ! command -v gh >/dev/null 2>&1 || ! gh --version >/dev/null 2>&1; then
  preflight_fail "gh CLI missing or broken" "gh auth login"
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${REPO_ROOT}/outputs/operator/productive_true_longrun_12h_v3/${RUN_ID}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/run.log"

echo "=== productive-longrun-12h-v3 start (${RUN_ID}) ===" | tee "${LOG_FILE}"
echo "preflight: queue=${PRODUCTIVE_QUEUE} profile=${PROFILE_NAME} max_tasks=${MAX_TASKS} max_prs=${MAX_PRS} early_completion=enabled" | tee -a "${LOG_FILE}"

DEV_LOOP_CMD=(
  "${PYTHON}" -m invis_alpha_os.cli.main operator-runner dev-loop
  --task-queue "${PRODUCTIVE_QUEUE}"
  --profile "${PROFILE_NAME}"
  --execute-dev-loop
  --create-pr
  --wait-ci
  --max-tasks "${MAX_TASKS}"
  --max-prs "${MAX_PRS}"
  --allow-early-completion
  --completion-notify
  --heartbeat-interval-minutes 10
  --continue-after-pr-limit heartbeat
  --continue-after-task-limit heartbeat
  --continue-on-task-failure
  --max-task-failures 8
  --max-same-failure-category 4
  --skip-existing-task-artifacts
  --failure-summary
  --stop-on-dirty-tree
)

set +e
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "${DEV_LOOP_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
else
  "${DEV_LOOP_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
fi
dev_loop_rc=${PIPESTATUS[0]}
set -e

latest_evidence="$(ls -td "${REPO_ROOT}"/outputs/operator/dev_loop/*/evidence_summary.json 2>/dev/null | head -1 || true)"
early_completion=""
stop_reason=""
if [[ -n "${latest_evidence}" && -f "${latest_evidence}" ]]; then
  stop_reason="$("${PYTHON}" -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('stop_reason',''))" "${latest_evidence}" 2>/dev/null || true)"
  early_completion="$("${PYTHON}" -c "import json,sys; d=json.load(open(sys.argv[1])); lr=d.get('longrun') or {}; print(lr.get('early_completion_detected', False))" "${latest_evidence}" 2>/dev/null || true)"
fi

if [[ "${dev_loop_rc}" -ne 0 ]]; then
  echo "${PRODUCTIVE_LABEL} FAILED: dev_loop_rc=${dev_loop_rc} log=${LOG_FILE}" | tee -a "${LOG_FILE}" >&2
  exit "${dev_loop_rc}"
fi

{
  echo "${PRODUCTIVE_LABEL} SUCCEEDED"
  echo "log: ${LOG_FILE}"
  [[ -n "${latest_evidence}" ]] && echo "evidence: ${latest_evidence}"
  [[ -n "${stop_reason}" ]] && echo "stop_reason: ${stop_reason}"
  if [[ "${early_completion}" == "True" ]]; then
    echo "note: early_completion_detected — review tasks_executed, prs_created, skip counts in evidence"
  fi
} | tee -a "${LOG_FILE}"

exit 0
