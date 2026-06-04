# Portfolio Data Quality Review v109

Date: 2026-06-04

## Decision

Add a source-only, fixture-only portfolio data-quality review before any raw-input quarantine or actual-import work.
The review aggregates existing validation and review contracts; it does not introduce another validator.

## Contract Relationships

- v98 sanitized/manual input is the upstream input candidate.
- v105 `portfolio_input` facade is the stable entry point for v98/v97/v95 validation and projection.
- v100 user-facing review supplies existing review-level parity context through the v105 report facade.
- v107 taxonomy normalizes two legacy keys and supplies categories without changing existing validators.

## Review Scope

- amount unit
- net worth, asset total, ratio total, and equity total consistency
- cash and individual-stock guardrails
- target allocation gap
- as-of month, unit, same-point-in-time values, and redacted-input manual confirmations

Structural consistency is displayed as `INFO`, guardrail/allocation attention as `WARN`, and existing validator failures as
`ERROR`. These labels describe data quality and constraints, not trade actions.

## Architecture Boundary

Do not move validation conditions or thresholds into v109. Do not connect v107 taxonomy back into existing validators.
The review may consume current contracts but must not become the canonical validator.

## Explicit Non-Approval

- workflow change or manual workflow_dispatch: not approved / not executed
- live HTTP, cache write, actual import, broker API, or raw Excel parsing: not approved / not executed
- env/secret display, dependency, pyproject, or Makefile change: not approved / not executed
- trading action or real email send: not approved / not executed
