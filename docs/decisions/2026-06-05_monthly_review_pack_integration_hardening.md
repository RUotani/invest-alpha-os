# Monthly Review Pack Integration Hardening

Date: 2026-06-05

## Decision

Add `monthly-review-pack-integration` as a source-only / fixture-only contract check for the monthly review pack.

## Rationale

The monthly decision sheet is now part of the same user-facing decision-support surface as weekly reports, portfolio
data quality review, operator dashboard summaries, and sample output contracts. It should therefore have an integration
check that verifies the important section markers, portfolio-quality connection, monthly input consistency connection,
target allocation gap reuse, and safety boundaries without changing report semantics.

## Contract

- CLI: `monthly-review-pack-integration`
- formats: `markdown`, `json`
- components checked:
  - `monthly_decision_sheet_v84`
  - `monthly_input_consistency_v95`
  - `portfolio_data_quality_review_v109`
  - `target_allocation_gap_v82`
- expected mode: `source_only_fixture_only_no_live_access`
- expected fixture month: `2026-05`
- expected severities: monthly input `WARN`, portfolio data quality `WARN`

## Boundary

- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import / manual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / real email send

## Follow-Up

If the monthly decision sheet UX changes, update the integration markers in the same PR and keep the weekly/monthly
golden snapshot regression aligned.
