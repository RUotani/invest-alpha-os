# Weekly Report Workflow Approval Patch Package v71

Date: 2026-05-31

## Decision

Add a source-only workflow approval package for Weekly Candidate Brief scheduling. The package converts v70D-v70F
findings into a concrete human approval decision without directly modifying `.github/workflows`.

## Root Cause

The weekly report did not appear on Saturday morning JST. From tracked source, the confirmed gap remains that no GitHub
Actions weekly schedule invokes `scripts/run_weekly_candidate_brief.sh`. A local launchd template exists, but source-only
inspection cannot prove that launchd is installed, loaded, awake, or healthy at runtime.

## Required Workflow Change

If GitHub Actions is the intended unattended scheduler, add a weekly workflow that runs at Saturday 07:00 Asia/Tokyo,
which maps to Friday 22:00 UTC:

```text
0 22 * * 5
```

## Exact Proposed Workflow Patch

The v71 report and CLI emit a copy-ready proposed patch for `.github/workflows/weekly_candidate_brief.yml`. The patch is
not applied by this milestone.

## Why Human Approval Is Required

`RULES.md` forbids direct `.github/workflows/*` changes without explicit human approval. This patch changes unattended
scheduled automation behavior, so it must remain a proposal until approved.

## Source-Only Fix Implemented

- Deterministic Saturday morning JST to UTC cron calculation.
- Current workflow state assessment.
- Missing-workflow and wrong-cron detection.
- Copy-ready workflow patch proposal.
- CLI/report/context pack integration.
- Tests for missing workflow, wrong cron, correct cron, patch rendering, and CLI/context status.

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- raw OHLCV persistence: not approved
- reports-private raw data write: not approved
- Git-tracked raw data write: not approved
- env/secret display: not approved
- `.github/workflows` direct change: not applied
- dependency / pyproject change: not applied
- trading action: not approved

## Next Decision Point

Prepare the local dry-run/backfill verification contract so the weekly report generation path can be verified before any
human-approved scheduler change is applied.
