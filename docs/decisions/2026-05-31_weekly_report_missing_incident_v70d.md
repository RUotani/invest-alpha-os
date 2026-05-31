# Weekly Report Missing Incident Diagnostic v70D

Date: 2026-05-31

## Decision

Record the user-observed incident that the Saturday morning JST weekly report did not appear, and add a source-only
diagnostic pack for Weekly Candidate Brief scheduling, delivery boundaries, UTC/JST cron mapping, and workflow repair
proposal.

## User-Observed Issue

Saturday morning JST weekly report did not appear.

## Root Cause Found

Confirmed from repo source:

- `scripts/run_weekly_candidate_brief.sh` exists and can generate Weekly Candidate Brief markdown/copy outputs.
- `ops/launchd/com.invest-alpha-os.weekly-candidate-brief.plist.template` exists and is configured for Saturday 07:00
  Asia/Tokyo.
- `.github/workflows/daily_report.yml` is `workflow_dispatch` only and does not define a weekly schedule.
- No tracked GitHub Actions weekly schedule invokes `scripts/run_weekly_candidate_brief.sh`.
- `weekly-candidate-brief-email` is dry-run by default; it writes previews and does not send Gmail unless separately
  gated.

Not proven from source-only inspection:

- Whether local launchd was installed, loaded, and healthy on the user's Mac.
- Whether a runtime launchd error occurred.
- Whether an external scheduler or GitHub Actions manual run was expected.

## Fix Implemented

- Added deterministic Saturday 07:00 JST to GitHub Actions UTC cron mapping.
- Added source inspection for weekly script, launchd template, and tracked GitHub workflow wiring.
- Added CLI/report output for the missing weekly report incident.
- Added ChatGPT context pack status.
- Added exact proposed GitHub Actions workflow patch as a proposal only.

## Workflow Change Requirement

A workflow change is required if unattended GitHub-hosted weekly delivery is the desired scheduler. It is not required if
the intended scheduler is local launchd and launchd is installed, loaded, and healthy.

The source-only repair does not modify `.github/workflows/*` because project rules require explicit human approval for
workflow changes.

## Exact Proposed Workflow Patch

```diff
diff --git a/.github/workflows/weekly_candidate_brief.yml b/.github/workflows/weekly_candidate_brief.yml
new file mode 100644
index 0000000..0000000
--- /dev/null
+++ b/.github/workflows/weekly_candidate_brief.yml
@@
+name: weekly-candidate-brief
+
+permissions:
+  contents: read
+
+on:
+  workflow_dispatch:
+  schedule:
+    - cron: "0 22 * * 5"  # Saturday 07:00 JST
+
+concurrency:
+  group: weekly-candidate-brief-${{ github.ref }}
+  cancel-in-progress: true
+
+jobs:
+  run-weekly-candidate-brief:
+    runs-on: ubuntu-latest
+    timeout-minutes: 20
+    permissions:
+      contents: read
+    steps:
+      - uses: actions/checkout@v4
+      - uses: actions/setup-python@v5
+        with:
+          python-version: "3.12"
+      - name: Install
+        run: |
+          python -m pip install --upgrade pip
+          python -m pip install -e ".[gmail]"
+      - name: Generate weekly candidate brief
+        run: scripts/run_weekly_candidate_brief.sh
+      - name: Upload weekly candidate brief artifact
+        uses: actions/upload-artifact@v4
+        with:
+          name: weekly-candidate-brief
+          path: |
+            reports/*/weekly_candidate_brief_v0_1.md
+            reports/*/weekly_candidate_brief_copy.md
+            reports/*/email/*
+            outputs/operator/weekly_candidate_brief/*/status.json
```

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- raw API response persistence: not approved
- reports-private raw data write: not approved
- Git-tracked raw data write: not approved
- env/secret display: not approved
- workflow changes: not applied
- trading action: not approved

## Next Decision Point

Choose one scheduler boundary:

- local launchd repair/verification, or
- explicit human approval for the proposed GitHub Actions weekly workflow.
