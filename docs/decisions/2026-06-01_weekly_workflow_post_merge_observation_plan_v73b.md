# Weekly Workflow Post-Merge Observation Plan v73B

Date: 2026-06-01

## Decision

After v73 added the approved Weekly Candidate Brief workflow, add a source-only post-merge observation plan for the next
Saturday 07:00 JST scheduled run.

## Scope

The v73B plan defines:

- expected GitHub Actions UI checks
- next scheduled run target and UTC/JST mapping
- artifact verification checklist
- failure triage path through v72C
- manual backfill decision path through v72B and v70F

## Non-Execution Boundary

This plan does not manually dispatch the workflow, inspect live GitHub logs, call providers, write cache, execute actual
refresh/import, persist raw data, display secrets, send Gmail, or perform trading action.

## Observation Target

- workflow: `.github/workflows/weekly_candidate_brief.yml`
- UTC cron: `0 22 * * 5`
- JST schedule: Saturday 07:00 Asia/Tokyo
- artifact: `weekly-candidate-brief`

## Failure Handling

If the scheduled run is absent, failed, or missing artifacts, classify the incident using the v72C triage matrix before
choosing any backfill action. Any manual backfill or Gmail send remains separately gated by human approval.

## Next Decision Point

After the next Saturday 07:00 JST scheduled run, record whether the workflow appeared, completed successfully, and
uploaded the expected artifact set.
