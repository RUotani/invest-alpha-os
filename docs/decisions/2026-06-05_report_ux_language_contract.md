# Report UX Language Contract

Date: 2026-06-05

## Decision

Add `report-ux-language-contract` as a source-only language contract for user-facing reports and operator summaries.

## Rationale

Weekly reports, monthly sheets, dashboard summaries, and sample contracts contain words such as high priority, WARN,
ERROR, review, preview, and NO-GO. These words must be interpreted consistently so the report is not mistaken for a
trade instruction, real email delivery, approved import, cache write, or broker operation.

The contract clarifies:

- candidates and monthly stances are not trading instructions
- high-priority review means review order, not execution permission
- ERROR / WARN / INFO are validation severity labels, not investment action labels
- email preview artifacts are inspection outputs, not Gmail delivery
- actual import, broker API, raw Excel direct parsing, and cache write remain NO-GO

## Boundary

- language contract only
- no scoring, veto, portfolio, monthly, or weekly generation semantics changed
- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import / manual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / real email send

## Follow-Up

Connect this language contract into the user guide consolidation so operators see the wording rules before running or
reviewing generated reports.
