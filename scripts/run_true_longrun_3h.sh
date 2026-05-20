#!/usr/bin/env bash
# R7.0-Ops-G2: guarded native true long-run (3h min-runtime, no auto-merge).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PYTHON="${PYTHON:-.venv/bin/python}"
export PYTHON

die() {
  echo "true-longrun-3h: ERROR: $*" >&2
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

echo "=== true-longrun-3h start ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="

set +e
"${PYTHON}" -m invis_alpha_os.cli.main operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue_longrun.yaml \
  --profile true_longrun_3h \
  --execute-dev-loop \
  --create-pr \
  --wait-ci \
  --max-tasks 50 \
  --max-prs 5 \
  --min-runtime-minutes 180 \
  --no-early-success-exit \
  --heartbeat-interval-minutes 10 \
  --continue-after-pr-limit heartbeat \
  --continue-after-task-limit heartbeat \
  --stop-on-failure \
  --stop-on-dirty-tree
dev_loop_rc=$?
set -e

echo "=== true-longrun-3h end (dev_loop_rc=${dev_loop_rc}) ==="
git status --short || true
if command -v gh >/dev/null 2>&1; then
  gh pr list --state open --limit 10 || true
fi

exit "${dev_loop_rc}"
