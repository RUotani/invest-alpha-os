# Weekly Report Workflow Patch Review and Human Approval Gate v72

Date: 2026-06-01

## Decision

Add a source-only human approval gate for the weekly candidate brief GitHub Actions workflow patch.

The gate freezes the proposed workflow behavior for human review: Saturday 07:00 JST weekly schedule, UTC cron
`0 22 * * 5`, manual `workflow_dispatch`, weekly candidate brief script invocation, and artifact upload paths. The
workflow file itself is not changed by this milestone.

## Root Cause

The weekly report missing incident remains actionable as a scheduler wiring gap: the tracked repository does not contain
an approved GitHub Actions weekly candidate brief workflow matching Saturday morning JST delivery.

## Required Workflow Change

- add `.github/workflows/weekly_candidate_brief.yml`
- include `workflow_dispatch`
- include cron `0 22 * * 5`, corresponding to Saturday 07:00 JST
- run `scripts/run_weekly_candidate_brief.sh`
- upload generated weekly report, copy, email preview, and operator status artifacts

## Why Human Approval Is Required

`RULES.md` and project instructions forbid direct `.github/workflows` changes without explicit human approval. This patch
would add unattended scheduled automation behavior and therefore must be reviewed and approved separately by the human
operator.

## Source-Only Work Implemented

- deterministic workflow patch review gate
- UTC/JST schedule display
- manual dispatch proposal
- failure detection matrix for scheduler, workflow, and silent failures
- context pack integration via `weekly_report_workflow_patch_review_gate_status`

## Explicit Non-Approval

- `.github/workflows` direct change: not approved
- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- actual refresh/import: not approved
- raw OHLCV/API persistence: not approved
- Gmail send: not approved
- trading action: not approved

## Next Decision Point

If the human approves the workflow patch, apply it in a dedicated workflow-change PR. Otherwise continue source-only
weekly report recovery hardening.
