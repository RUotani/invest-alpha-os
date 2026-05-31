# Scheduled Report Observability and Missing-Report Sentinel v70E

Date: 2026-05-31

## Decision

Add a source-only scheduled report observability pack so a missed Weekly Candidate Brief can be detected from redacted
artifact/status metadata before the user notices manually.

## Rationale

v70D identified that the Saturday morning JST weekly report incident cannot be fully proven from source-only inspection,
but the repo can still model the expected occurrence, grace window, artifact/status paths, and missing-report verdict.

## Sentinel Boundary

- The sentinel checks path existence metadata only.
- It does not read raw market data.
- It does not read report body content.
- It does not send Gmail.
- It does not create GitHub issues.
- It does not edit workflows.

## Expected Schedule

| Item | Value |
|---|---|
| report kind | weekly |
| expected local time | Saturday 07:00 Asia/Tokyo |
| GitHub Actions UTC cron equivalent | `0 22 * * 5` |
| default grace period | 6 hours |
| default lookback | 10 days |

## Missing-Report Verdicts

- `expected_report_present`
- `warn_report_present_status_missing`
- `missing_report_detected_source_artifact_absent`
- `not_checked`

## Required Manual Wiring

The sentinel must be run manually or wired to a separately approved scheduler. Any `.github/workflows/*` change still
requires explicit human approval.

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
- Gmail send: not approved
- workflow changes: not applied
- trading action: not approved

## Next Decision Point

Prepare a weekly report recovery runbook and manual backfill approval pack, still source-only, so the operator has a
safe response when the sentinel reports `missing_report_detected_source_artifact_absent`.
