# Weekly Artifact Local Verification Harness

Date: 2026-06-05

## Decision

Add a source-only local verification harness for weekly candidate brief artifacts before the 2026-06-06 natural
scheduled-run observation is available.

## Rationale

P1 scheduled natural run observation is not yet observable at 2026-06-05 19:58 JST. The next useful source-side work is
to make artifact verification repeatable once a scheduled run or local runner output exists.

The harness verifies generated artifacts and `status.json` without dispatching workflows, changing workflow files,
fetching live provider data, writing cache, importing actual data, parsing raw broker/Excel files, showing secrets, or
sending email.

## Contract

- CLI: `weekly-artifact-local-verify`
- inputs: `--report-date`, optional `--report-dir`, optional `--status-file`, `--format markdown|json`
- default report location: `reports/<report-date>`
- default status location: `outputs/operator/weekly_candidate_brief/<report-date>/status.json`
- required local runner artifacts:
  - `weekly_candidate_brief_v0_1.md`
  - `weekly_candidate_brief_copy.md`
  - `weekly_candidate_brief.json`
  - `email/email_preview.txt`
  - `email/email_preview.html`
  - `status.json`
- status contract: v104 schema, `gmail_send_attempted=false`, matching report date, and complete artifact generation

## Boundary

- workflow_dispatch: not approved by this pack
- workflow direct change: not approved by this pack
- provider live HTTP / market-data live fetch: not approved
- cache write / actual import: not approved
- broker API / raw Excel direct parsing: not approved
- real email send: not approved
- trading action: not approved

## Follow-Up

After 2026-06-06 07:30 JST, run read-only scheduled observation first. If a schedule-triggered artifact bundle exists,
use this local verification contract to classify missing artifacts, v104 schema issues, and email-send boundary issues.
