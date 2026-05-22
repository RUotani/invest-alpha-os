#!/usr/bin/env bash
# R7.0-Ops-I7: human-gated productive PR merge helper (NOT autonomous; no force merge).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

die() {
  echo "merge-productive-prs: ERROR: $*" >&2
  exit 1
}

if [[ "${CONFIRM_PRODUCTIVE_PR_MERGE:-}" != "YES" ]]; then
  die "CONFIRM_PRODUCTIVE_PR_MERGE=YES is required"
fi

if ! command -v gh >/dev/null 2>&1; then
  die "gh CLI not found"
fi

PRS_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prs)
      PRS_ARG="${2:-}"
      shift 2
      ;;
    *)
      die "unknown argument: $1 (use --prs 115-132 or --prs 115,116)"
      ;;
  esac
done

if [[ -z "${PRS_ARG}" ]]; then
  die "--prs is required (example: --prs 115-132)"
fi

expand_prs() {
  local token="$1"
  if [[ "${token}" == *-* ]]; then
    local start="${token%%-*}"
    local end="${token##*-}"
    seq "${start}" "${end}"
  else
    echo "${token}" | tr ',' ' '
  fi
}

MERGED=()
FAILED=""

for pr in $(expand_prs "${PRS_ARG}"); do
  echo "=== PR #${pr}: checks ==="
  if ! gh pr checks "${pr}" --watch; then
    FAILED="${pr}"
    echo "merge-productive-prs: STOP checks failed for PR #${pr}" >&2
    break
  fi
  echo "=== PR #${pr}: merge (squash, keep branch) ==="
  if ! gh pr merge "${pr}" --squash --delete-branch=false; then
    FAILED="${pr}"
    echo "merge-productive-prs: STOP merge failed for PR #${pr}" >&2
    break
  fi
  MERGED+=("${pr}")
done

echo "merge-productive-prs: merged=${#MERGED[@]} prs=[${MERGED[*]:-}]"
if [[ -n "${FAILED}" ]]; then
  echo "merge-productive-prs: failed_at PR #${FAILED}" >&2
  exit 1
fi

echo "next action (manual): git fetch origin main --prune && git checkout main && git pull"
exit 0
