#!/usr/bin/env bash
# If GitHub CLI is available, show the latest Actions run status (read-only).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "=== post-push-check ==="

if ! command -v gh >/dev/null 2>&1; then
  echo "warning: gh CLI not found; skipping GitHub Actions lookup (exit 0)" >&2
  exit 0
fi

echo "Fetching latest workflow run via gh ..."
# JSON only — no secrets expected in workflow metadata.
if ! gh_run_json="$(gh run list -L 1 --json databaseId,name,status,conclusion,headBranch,event,workflowName,updatedAt 2>/dev/null)"; then
  echo "warning: gh run list failed (auth or network); exiting 0" >&2
  exit 0
fi

echo "${gh_run_json}" | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
if not raw:
    print("warning: gh returned empty run list; exiting")
    sys.exit(0)
data = json.loads(raw)
if not data:
    print("warning: no runs returned")
    sys.exit(0)
r = data[0]
print("Latest run:")
for k in ("workflowName", "name", "status", "conclusion", "headBranch", "event", "updatedAt", "databaseId"):
    if k in r and r[k] is not None:
        print(f"  {k}: {r[k]}")
wid = r.get("databaseId")
if wid:
    print(f"  view: gh run view {wid}")
'
echo "=== end post-push-check ==="
