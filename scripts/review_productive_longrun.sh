#!/usr/bin/env bash
# R7.0-Ops-I7: read-only productive longrun post-run review (no git changes).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

RUN_ID="${1:-}"
export PATH="${REPO_ROOT}/.venv/bin:${PATH}"
PYTHON="${PYTHON:-${REPO_ROOT}/.venv/bin/python}"

ARGS=(operator-runner post-run-review --format markdown)
if [[ -n "${RUN_ID}" ]]; then
  ARGS+=(--run-id "${RUN_ID}")
fi

"${PYTHON}" -m invis_alpha_os.cli.main "${ARGS[@]}"
