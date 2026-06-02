# Scheduled Run Observation Readiness v101

Date: 2026-06-03

## Decision

Add a source-only scheduled-run observation readiness contract for the weekly candidate brief. The contract lists the
expected scheduled artifacts, the minimum markers that should appear in each artifact, and a fixture-only validator that
can be run before the scheduled observation window.

## Rationale

The next weekly scheduled-run observation should happen after `2026-06-06 07:30 JST`. This pack reduces the work needed
at observation time by making the artifact checklist explicit before the run. It does not dispatch the workflow, change
workflow files, send email, fetch market/provider data, or write cache/import outputs.

The expected schedule remains `0 22 * * 5 UTC`, corresponding to Saturday 07:00 JST. Observation should happen after a
buffer, currently recorded as 2026-06-06 07:30 JST.

## Artifact Expectations

- `weekly_candidate_brief_v0_1.md`
- `weekly_candidate_brief_copy.md`
- `weekly_candidate_brief.json`
- `email/email_preview.txt`
- `email/email_preview.html`
- `status.json`

Each required artifact must preserve the relevant weekly-report markers, especially Score / Veto, pipeline trace,
Sanitized / Manual Input, cash 11.7%, individual stocks 19.6%, and non-trading safety wording.

## Explicit Non-Approval

- workflow change: not approved / not changed
- manual workflow_dispatch: not approved / not executed
- provider live HTTP or market-data live fetch: not approved / not executed
- cache write: not approved / not executed
- actual import or manual actual import: not approved / not executed
- broker API or raw broker export parsing: not approved / not executed
- raw Excel direct parsing: not approved / not executed
- env/secret display: not approved / not executed
- dependency / pyproject / Makefile change: not approved / not changed
- trading action, order placement, auto-trading, or real email: not approved / not executed

## Next Decision Point

After the scheduled workflow window, perform v86 scheduled run observation using this checklist against the actual
artifact set. Do not use manual workflow_dispatch for this observation.
