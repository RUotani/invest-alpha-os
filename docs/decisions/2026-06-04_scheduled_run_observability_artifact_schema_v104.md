# Scheduled Run Observability and Artifact Schema v104

Date: 2026-06-04

## Decision

Extend the weekly candidate brief `status.json` into a structured observation record while retaining all legacy fields.
The status record becomes the primary machine-readable artifact for distinguishing scheduled, workflow-dispatch, and
local runs and for confirming report/email-preview generation without sending email.

## Rationale

v86 was partial because the expected natural scheduled run was not observed. The earlier workflow-dispatch reference run
confirmed weekly report, copy report, and email preview generation, but marker-only artifact inspection could not explain
whether a run was scheduled, manually dispatched, or local. Gmail non-delivery remains expected because real email send
is prohibited.

Marker-based observation is also fragile when fixture values or report wording change. v104 therefore moves the primary
observation contract toward structured status fields and leaves minimal semantic markers as secondary evidence.

## Schema

Legacy fields retained:

- `date`
- `status`
- `full_report`
- `copy_report`
- `completed_at`

Structured fields added:

- `schema_version: v104`
- `source_mode: observation_only_no_live_http`
- `dry_run: true`
- `trigger.event_name`, `workflow`, `run_id`, `run_attempt`, `sha`, `ref`
- `reports.full_report`, `copy_report`, `json_report`
- `email_preview.text`, `html`, `eml`, `gmail_send_attempted: false`
- `observation.expected_markers`, `artifact_generation_complete`, `status_file`

Only the safe GitHub metadata environment keys needed by the trigger record are read. No environment values are logged.
Unknown events are classified as `unknown`; missing GitHub event metadata is classified as `local`.

## v101 Checklist Refinement

The v101 observation checklist now prioritizes artifact presence plus v104 status schema fields. Fixed fixture numbers
such as cash 11.7% and individual stocks 19.6% are no longer required marker strings for observation readiness. The
current runner does not generate a weekly JSON report, so that artifact is optional and `reports.json_report` remains
nullable; `status.json` is required.

## Explicit Non-Approval

- workflow or schedule change: not approved / not changed
- manual workflow_dispatch: not approved / not executed
- provider live HTTP or market-data live fetch: not approved / not executed
- cache write: not approved / not executed
- actual import or manual actual import: not approved / not executed
- broker API, broker login, raw broker export parsing, or raw Excel direct parsing: not approved / not executed
- raw broker/OHLCV/API persistence or reports-private raw data write: not approved / not executed
- env/secret display: not approved / not executed
- dependency / pyproject / Makefile change: not approved / not changed
- trading action, order placement, auto-trading, or real email: not approved / not executed

## Remaining Limit

The status schema improves observability after a run starts, but it cannot prove why GitHub Actions failed to create a
scheduled run. Scheduled-trigger visibility remains a separate platform observation problem.
