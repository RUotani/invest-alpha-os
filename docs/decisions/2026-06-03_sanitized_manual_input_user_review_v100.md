# Sanitized Manual Input User Review v100

Date: 2026-06-03

## Decision

Add a source-only, fixture-only user-facing review layer for the v98 sanitized/manual input contract. The review turns
the redacted portfolio context into Japanese summary lines, guardrail review items, next checks, and explicit
non-approval boundaries.

## Rationale

v98 validates sanitized/manual input, v97 carries the portfolio context, v95 checks monthly consistency, and v99 connects
the short summary into weekly report surfaces. v100 adds a user-facing explanation layer so the weekly and strategy
workflow can show why cash pressure and individual stock allocation matter without implying a trade instruction.

The current redacted fixture is `2026-05 / JPY / man_yen`. It remains `WARN` because cash is below the 15% minimum
guardrail and individual stocks exceed the 10-15% target band. The warning is a guardrail condition, not a source data
import, broker access, or trading action.

## Scope

- Build a `SanitizedManualInputUserReviewV100` contract.
- Render copy-ready Markdown with summary, key review items, next checks, and explicit non-approval.
- Preserve v98/v97/v95/v99 parity and avoid contradictory wording.
- Keep JFE/Honda or other single-symbol logic out of this layer.

## Explicit Non-Approval

- workflow change: not approved / not changed
- manual workflow_dispatch: not approved / not executed
- provider live access or live HTTP: not approved / not executed
- cache write: not approved / not executed
- actual import: not approved / not executed
- broker API or raw broker export parsing: not approved / not executed
- raw Excel direct parsing: not approved / not executed
- env/secret display: not approved / not executed
- trading action or order placement: not approved / not executed

## Next Decision Point

After v100 is merged, v101 can add a scheduled-run observation readiness pack that prepares the next weekly run review
without dispatching workflows or changing workflow files.
