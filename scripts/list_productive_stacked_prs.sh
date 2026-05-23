#!/usr/bin/env bash
# R7.0-Ops-I9 G1: read-only stacked PR listing for productive long-run consolidation.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

BRANCH_PREFIX="${1:-work/dev-loop/autonomous}"
STOP=0

if ! command -v gh >/dev/null 2>&1; then
  echo "list_productive_stacked_prs: gh CLI not found" >&2
  exit 2
fi

echo "=== productive stacked PRs (prefix=${BRANCH_PREFIX}) ==="
if ! gh pr list --state open --limit 100 --json number,title,headRefName,mergeable,url \
  | "${REPO_ROOT}/.venv/bin/python" -c "
import json, sys
prefix = sys.argv[1].lower()
rows = json.load(sys.stdin)
hits = [r for r in rows if prefix in (r.get('headRefName') or '').lower()]
for r in sorted(hits, key=lambda x: x['number']):
    print(f\"#{r['number']} mergeable={r.get('mergeable')} {r['headRefName']} {r['title']}\")
    print(f\"  {r['url']}\")
if not hits:
    print('(no open PRs for prefix)')
if rows and len(hits) == len(rows) and len(hits) >= 5:
    print('note: many stacked PRs — consider #165-style consolidation onto origin/main')
" "${BRANCH_PREFIX}"; then
  STOP=1
  echo "list_productive_stacked_prs: gh pr list failed" >&2
fi

echo "=== suggested consolidation branch ==="
echo "work/r7-0-ops-consolidate-$(date -u +%Y%m%d)"

if [[ "${STOP}" -ne 0 ]]; then
  exit 2
fi
exit 0
- dev-loop smoke marker: 20260523T035415Z (2026-05-23T03:55:24Z)
