#!/usr/bin/env bash
# R7.0-Ops-I10: productive 12h v2 bounded long-run (early completion + completion notify; no auto-merge).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

export PATH="${REPO_ROOT}/.venv/bin:${PATH}"
PYTHON="${PYTHON:-${REPO_ROOT}/.venv/bin/python}"
export PYTHON

PRODUCTIVE_QUEUE="${PRODUCTIVE_QUEUE:-config/tasks/autonomous_dev_queue_productive_12h_v2.yaml}"
PROFILE_NAME="true_longrun_12h_bounded"
PROFILE_FILE="config/operator_dev_loop_profiles.yaml"
PRODUCTIVE_LABEL="PRODUCTIVE-LONGRUN-12H-V2"
MIN_RUNTIME_MINUTES=720
MAX_PRS=12

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
  preflight_fail "working tree is dirty" "commit, stash, or discard changes before starting 12h v2 run"
fi

if pgrep -f "operator-runner dev-loop" >/dev/null 2>&1; then
  preflight_fail "another operator-runner dev-loop process is running" "stop the other run before starting 12h v2 productive longrun"
fi

if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  preflight_fail ".venv/bin/python missing or not executable" "create venv and install project dependencies"
fi

if [[ -x "${REPO_ROOT}/.venv/bin/pytest" ]]; then
  if ! "${REPO_ROOT}/.venv/bin/pytest" --version >/dev/null 2>&1; then
    preflight_fail "pytest not runnable via .venv/bin/pytest" "reinstall pytest in .venv: pip install pytest"
  fi
elif ! "${REPO_ROOT}/.venv/bin/python" -m pytest --version >/dev/null 2>&1; then
  preflight_fail "pytest not available (.venv/bin/pytest and python -m pytest)" \
    "ensure PATH includes .venv/bin; run: .venv/bin/python -m pytest --version"
fi

if [[ ! -f "${REPO_ROOT}/${PRODUCTIVE_QUEUE}" ]]; then
  preflight_fail "task queue not found: ${PRODUCTIVE_QUEUE}" "merge I10 queue or fix path"
fi

if [[ ! -f "${REPO_ROOT}/${PROFILE_FILE}" ]]; then
  preflight_fail "profile file not found: ${PROFILE_FILE}" "ensure config/operator_dev_loop_profiles.yaml exists"
fi

if ! command -v gh >/dev/null 2>&1; then
  preflight_fail "gh CLI not found" "install GitHub CLI and authenticate: gh auth login"
fi

if ! gh --version >/dev/null 2>&1; then
  preflight_fail "gh --version failed" "fix GitHub CLI installation or auth"
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${REPO_ROOT}/outputs/operator/productive_true_longrun_12h_v2/${RUN_ID}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/run.log"

echo "=== productive-longrun-12h-v2 start (${RUN_ID}) ===" | tee "${LOG_FILE}"
echo "preflight: gates ok, queue=${PRODUCTIVE_QUEUE}, profile=${PROFILE_NAME} max_prs=${MAX_PRS} early_completion=enabled" | tee -a "${LOG_FILE}"

DEV_LOOP_CMD=(
  "${PYTHON}" -m invis_alpha_os.cli.main operator-runner dev-loop
  --task-queue "${PRODUCTIVE_QUEUE}"
  --profile "${PROFILE_NAME}"
  --execute-dev-loop
  --create-pr
  --wait-ci
  --max-tasks 40
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

STOP=0
set +e
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "${DEV_LOOP_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
else
  echo "productive-longrun-12h-v2: WARN: caffeinate not found; continuing without sleep guard" | tee -a "${LOG_FILE}"
  "${DEV_LOOP_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
fi
dev_loop_rc=${PIPESTATUS[0]}
set -e
if [[ "${dev_loop_rc}" -ne 0 ]]; then
  STOP=1
fi

latest_evidence="$(ls -td "${REPO_ROOT}"/outputs/operator/dev_loop/*/evidence_summary.json 2>/dev/null | head -1 || true)"
stop_reason=""
early_completion=""
if [[ -n "${latest_evidence}" && -f "${latest_evidence}" ]]; then
  stop_reason="$("${PYTHON}" -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('stop_reason',''))" "${latest_evidence}" 2>/dev/null || true)"
  early_completion="$("${PYTHON}" -c "import json,sys; d=json.load(open(sys.argv[1])); lr=d.get('longrun') or {}; print(lr.get('early_completion_detected', False))" "${latest_evidence}" 2>/dev/null || true)"
fi

classify_outcome=""
if [[ -n "${latest_evidence}" && -f "${latest_evidence}" ]]; then
  classify_outcome="$("${PYTHON}" "${REPO_ROOT}/scripts/productive_longrun_classify.py" \
    "${latest_evidence}" "${dev_loop_rc}" "${MIN_RUNTIME_MINUTES}" "${MAX_PRS}" 2>/dev/null || true)"
fi

if [[ "${STOP}" -ne 0 ]]; then
  if [[ "${classify_outcome}" == "interrupted_after_productive_cap" ]]; then
    fail_banner="${PRODUCTIVE_LABEL} INTERRUPTED_AFTER_PRODUCTIVE_CAP: dev_loop_rc=${dev_loop_rc}"
  elif [[ "${stop_reason}" == max_task_failures* || "${stop_reason}" == max_same_failure_category* ]]; then
    fail_banner="${PRODUCTIVE_LABEL} FAILED: ${stop_reason}"
  else
    fail_banner="${PRODUCTIVE_LABEL} FAILED: dev_loop_rc=${dev_loop_rc}"
  fi
  {
    echo "${fail_banner}"
    echo "log: ${LOG_FILE}"
    if [[ -n "${latest_evidence}" ]]; then
      echo "evidence: ${latest_evidence}"
    fi
    echo "--- last 80 lines of run.log ---"
    tail -n 80 "${LOG_FILE}" 2>/dev/null || true
    echo "next action: inspect log and evidence; merge green PRs manually"
  } | tee -a "${LOG_FILE}" >&2
  exit "${dev_loop_rc}"
fi

failed_count=0
skipped_count=0
if [[ -n "${latest_evidence}" && -f "${latest_evidence}" ]]; then
  read -r failed_count skipped_count <<< "$("${PYTHON}" -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d.get('failed_tasks') or []), len(d.get('skipped_tasks') or []))" "${latest_evidence}" 2>/dev/null || echo '0 0')"
fi
if [[ "${failed_count}" -gt 0 || "${skipped_count}" -gt 0 ]]; then
  banner="${PRODUCTIVE_LABEL} SUCCEEDED_WITH_RECORDED_FAILURES: failed_tasks=${failed_count} skipped_tasks=${skipped_count}"
else
  banner="${PRODUCTIVE_LABEL} SUCCEEDED"
fi
{
  echo "${banner}"
  echo "log: ${LOG_FILE}"
  if [[ -n "${latest_evidence}" ]]; then
    echo "evidence: ${latest_evidence}"
  fi
  if [[ -n "${stop_reason}" ]]; then
    echo "stop_reason: ${stop_reason}"
  fi
  if [[ "${early_completion}" == "True" ]]; then
    echo "note: early_completion_detected; dev-loop emitted completion notification (best-effort)"
  else
    echo "note: min_runtime durability path or partial run; review longrun block in evidence"
  fi
  echo "utilization: review tasks_executed, prs_created, early_completion_* fields in evidence"
} | tee -a "${LOG_FILE}"

git status --short 2>&1 | tee -a "${LOG_FILE}" || true
if command -v gh >/dev/null 2>&1; then
  echo "--- open PRs ---" | tee -a "${LOG_FILE}"
  gh pr list --state open --limit 25 2>&1 | tee -a "${LOG_FILE}" || true
fi

exit 0
