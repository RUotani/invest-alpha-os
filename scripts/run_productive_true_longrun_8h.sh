#!/usr/bin/env bash
# R7.0-Ops-I3: productive 8h guarded long-run (fail-fast preflight + failure policy; no auto-merge).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

export PATH="${REPO_ROOT}/.venv/bin:${PATH}"
PYTHON="${PYTHON:-${REPO_ROOT}/.venv/bin/python}"
export PYTHON

PRODUCTIVE_QUEUE="config/tasks/autonomous_dev_queue_productive_8h.yaml"
PROFILE_FILE="config/operator_dev_loop_profiles.yaml"

preflight_fail() {
  echo "PRODUCTIVE-LONGRUN-8H PREFLIGHT FAILED: $1" >&2
  echo "next action: $2" >&2
  exit 1
}

notify_optional() {
  local title="$1"
  local message="$2"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${message}\" with title \"${title}\"" >/dev/null 2>&1 || true
  fi
}

if [[ "${CONFIRM_OPERATOR_DEV_LOOP:-}" != "YES" ]]; then
  preflight_fail "CONFIRM_OPERATOR_DEV_LOOP=YES is not set" "export CONFIRM_OPERATOR_DEV_LOOP=YES"
fi
if [[ "${CONFIRM_GITHUB_PR_CREATE:-}" != "YES" ]]; then
  preflight_fail "CONFIRM_GITHUB_PR_CREATE=YES is not set" "export CONFIRM_GITHUB_PR_CREATE=YES"
fi

if [[ -n "$(git status --short)" ]]; then
  preflight_fail "working tree is dirty" "commit, stash, or discard changes before starting 8h run"
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
  preflight_fail "task queue not found: ${PRODUCTIVE_QUEUE}" "merge Ops-I queue or fix path"
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
LOG_DIR="${REPO_ROOT}/outputs/operator/productive_true_longrun_8h/${RUN_ID}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/run.log"

echo "=== productive-longrun-8h start (${RUN_ID}) ===" | tee "${LOG_FILE}"
echo "preflight: gates ok, pytest ok, queue=${PRODUCTIVE_QUEUE}, profile=true_longrun_8h" | tee -a "${LOG_FILE}"

DEV_LOOP_CMD=(
  "${PYTHON}" -m invis_alpha_os.cli.main operator-runner dev-loop
  --task-queue "${PRODUCTIVE_QUEUE}"
  --profile true_longrun_8h
  --execute-dev-loop
  --create-pr
  --wait-ci
  --max-tasks 100
  --max-prs 10
  --min-runtime-minutes 480
  --no-early-success-exit
  --heartbeat-interval-minutes 10
  --continue-after-pr-limit heartbeat
  --continue-after-task-limit heartbeat
  --continue-on-task-failure
  --max-task-failures 3
  --failure-summary
  --stop-on-dirty-tree
)

set +e
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "${DEV_LOOP_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
else
  echo "productive-longrun-8h: WARN: caffeinate not found; continuing without sleep guard" | tee -a "${LOG_FILE}"
  "${DEV_LOOP_CMD[@]}" 2>&1 | tee -a "${LOG_FILE}"
fi
dev_loop_rc=${PIPESTATUS[0]}
set -e

latest_evidence="$(ls -td "${REPO_ROOT}"/outputs/operator/dev_loop/*/evidence_summary.json 2>/dev/null | head -1 || true)"
stop_reason=""
if [[ -n "${latest_evidence}" && -f "${latest_evidence}" ]]; then
  stop_reason="$("${PYTHON}" -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('stop_reason',''))" "${latest_evidence}" 2>/dev/null || true)"
fi

if [[ "${dev_loop_rc}" -ne 0 ]]; then
  if [[ "${stop_reason}" == max_task_failures* ]]; then
    fail_banner="PRODUCTIVE-LONGRUN-8H FAILED: ${stop_reason}"
  else
    fail_banner="PRODUCTIVE-LONGRUN-8H FAILED: dev_loop_rc=${dev_loop_rc}"
  fi
  {
    echo "${fail_banner}"
    echo "log: ${LOG_FILE}"
    if [[ -n "${latest_evidence}" ]]; then
      echo "evidence: ${latest_evidence}"
    fi
    echo "--- last 80 lines of run.log ---"
    tail -n 80 "${LOG_FILE}" 2>/dev/null || true
    echo "next action: inspect log and evidence; fix pytest/path/gates; do not assume 8h success"
  } | tee -a "${LOG_FILE}" >&2
  notify_optional "productive-longrun-8h" "FAILED rc=${dev_loop_rc}"
  exit "${dev_loop_rc}"
fi

failed_count=0
if [[ -n "${latest_evidence}" && -f "${latest_evidence}" ]]; then
  failed_count="$("${PYTHON}" -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d.get('failed_tasks') or []))" "${latest_evidence}" 2>/dev/null || echo 0)"
fi
if [[ "${failed_count}" -gt 0 ]]; then
  banner="PRODUCTIVE-LONGRUN-8H SUCCEEDED_WITH_RECORDED_FAILURES: failed_tasks=${failed_count}"
else
  banner="PRODUCTIVE-LONGRUN-8H SUCCEEDED"
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
  if [[ "${failed_count}" -gt 0 ]]; then
    echo "next action: review failure-summary and failed_tasks in evidence after run"
  fi
  echo "note: heartbeat_waiting is normal before min_runtime; success target is min_runtime reached: 480"
} | tee -a "${LOG_FILE}"

git status --short 2>&1 | tee -a "${LOG_FILE}" || true
if command -v gh >/dev/null 2>&1; then
  echo "--- open PRs ---" | tee -a "${LOG_FILE}"
  gh pr list --state open --limit 10 2>&1 | tee -a "${LOG_FILE}" || true
fi

notify_optional "productive-longrun-8h" "SUCCEEDED ${stop_reason:-completed}"
exit 0
