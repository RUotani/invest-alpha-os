# Operator User Guide Consolidation

Date: 2026-06-05

## Decision

Add `docs/operator_user_guide.md` as the consolidated entry point for weekly/monthly report review, artifact
verification, operator summaries, consistency checks, and sample regeneration boundaries.

## Rationale

The repo now has several safe source-only/read-only CLI surfaces. Without one guide, an operator can confuse artifact
preview with Gmail delivery, sample regeneration contract with file writes, or scheduled observation with manual
workflow dispatch.

The guide consolidates:

- safe command index
- natural scheduled run observation classification
- artifact verification rules
- email preview vs Gmail delivery
- monthly review integration check
- report UX language rules
- forbidden hard-gate actions

## Boundary

- docs-only consolidation plus docs marker tests
- no workflow change
- no manual workflow_dispatch
- no live HTTP / market-data live fetch
- no cache write / actual import / manual import
- no broker API / raw Excel direct parsing
- no env/secret display
- no trading action / real email send

## Follow-Up

Keep this guide as the first operator-facing reference when adding future report/review CLIs.
