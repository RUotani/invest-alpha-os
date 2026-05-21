#!/usr/bin/env bash
# R7.0-Ops-I: productive 8h guarded long-run (large task queue, no auto-merge).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PYTHON="${PYTHON:-.venv/bin/python}"
export PYTHON

die() {
  echo "productive-longrun-8h: ERROR: $*" >&2
  exit 1
}

if [[ "${CONFIRM_OPERATOR_DEV_LOOP:-}" != "YES" ]]; then
  die "CONFIRM_OPERATOR_DEV_LOOP=YES is required"
fi
if [[ "${CONFIRM_GITHUB_PR_CREATE:-}" != "YES" ]]; then
  die "CONFIRM_GITHUB_PR_CREATE=YES is required"
fi

if [[ -n "$(git status --short)" ]]; then
  die "dirty working tree; resolve or stash before long-run"
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${ROOT}/outputs/operator/productive_true_longrun_8h/${RUN_ID}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/run.log"

echo "=== productive-longrun-8h start (${RUN_ID}) ===" | tee "${LOG_FILE}"

DEV_LOOP_CMD=(
  "${PYTHON}" -m invis_alpha_os.cli.main operator-runner dev-loop
  --task-queue config/tasks/autonomous_dev_queue_productive_8h.yaml
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
  --stop-on-failure
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

echo "=== productive-longrun-8h end (dev_loop_rc=${dev_loop_rc}) log=${LOG_FILE} ===" | tee -a "${LOG_FILE}"
git status --short 2>&1 | tee -a "${LOG_FILE}" || true
if command -v gh >/dev/null 2>&1; then
  gh pr list --state open --limit 10 2>&1 | tee -a "${LOG_FILE}" || true
fi
latest_evidence="$(ls -td "${ROOT}"/outputs/operator/dev_loop/*/evidence_summary.json 2>/dev/null | head -1 || true)"
if [[ -n "${latest_evidence}" ]]; then
  echo "productive-longrun-8h: latest evidence=${latest_evidence}" | tee -a "${LOG_FILE}"
fi

exit "${dev_loop_rc}"
