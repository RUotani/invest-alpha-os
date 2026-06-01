# Weekly Candidate Brief Workflow v73

Date: 2026-06-01

## Decision

Apply a dedicated PR after explicit human approval to add the Weekly Candidate Brief GitHub Actions workflow. The only
direct `.github/workflows` modification allowed by this decision is the new Weekly Candidate Brief workflow file.

## Schedule

- UTC cron: `0 22 * * 5`
- JST schedule: Saturday 07:00 Asia/Tokyo
- manual dispatch: available via `workflow_dispatch`

## Approved Direct Workflow Scope

This PR is allowed to directly change only this workflow file:

- `.github/workflows/weekly_candidate_brief.yml`

The workflow runs `scripts/run_weekly_candidate_brief.sh` and uploads the generated weekly report artifacts:

- `reports/*/weekly_candidate_brief_v0_1.md`
- `reports/*/weekly_candidate_brief_copy.md`
- `reports/*/email/*`
- `outputs/operator/weekly_candidate_brief/*/status.json`

## Why This Direct Workflow Change Is Allowed

The human operator explicitly approved this single workflow-only PR after v72 recorded the workflow patch as ready for
human approval. The approval does not extend to any other workflow, dependency, pyproject, provider, cache, import, raw
data, or trading change.

Supporting source diagnostics and tests may be updated in the same PR so the repository state no longer reports the
weekly workflow as missing after this approved workflow is added.

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- Tiingo API call: not approved
- Stooq / Yahoo / Polygon live fetch: not approved
- cache write: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- raw OHLCV persistence: not approved
- raw API response persistence: not approved
- reports-private raw data write: not approved
- Git-tracked raw data write: not approved
- env/secret display: not approved
- dependency / pyproject changes: not approved
- broker/manual raw data handling: not approved
- trading action: not approved

## Remaining Observation Requirement

After merge, do not manually dispatch this workflow unless separately approved. Observe the next Saturday 07:00 JST
scheduled run and verify workflow status, uploaded artifacts, and v72C triage readiness.

## Source Diagnostic Follow-Up

The v70D source diagnostic and focused tests now recognize the tracked weekly GitHub Actions schedule after this v73
workflow is added. The diagnostic still remains source-only and does not inspect runtime GitHub logs, manually dispatch
the workflow, display secrets, call providers, write cache, or execute imports.
