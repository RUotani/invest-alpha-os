# Versionless Facade Introduction v105

Date: 2026-06-04

## Decision

Add thin versionless facades for report view models, portfolio input, and the candidate pipeline. Existing versioned
modules remain the implementation and historical record. The facades contain aliases and explicit exports only; they do
not add business logic, I/O, validation semantics, or execution paths.

## Rationale

Direct cross-version imports from v90-v104 modules make new code depend on historical implementation names. That
increases migration cost and encourages newer concepts to be added to older versioned modules. A thin stable import
surface reduces that pressure without a destructive refactor.

This change deliberately avoids replacing existing imports in bulk. Existing modules and behavior remain available, and
current call sites can migrate only when they are otherwise being changed.

## Facades

### `report_view_model.py`

- Stable aliases for the v96 weekly/email shared view model.
- Stable access to v99 sanitized/manual summary and v100 user-facing review.
- Stable access to v104 artifact status build/validation.

### `portfolio_input.py`

- Treats v98 sanitized/manual input as the preferred upstream entry point for new code.
- Exposes v97 portfolio-context projection and allocation-gap validation.
- Exposes v95 monthly consistency validation as a downstream validation path.

This does not complete v98 canonicalization. A future change may formalize v98 as canonical and v97/v95 as
projection/validator layers.

### `candidate_pipeline.py`

- Stable aliases for v90 traceability, v91 scoring, v92 vetoes, and v93 integrated assessment.
- Keeps score-band and action-label terminology unchanged.
- Does not rename `HIGH_CONVICTION_REVIEW`.

## Contributor Guidance

For new code:

- Prefer `invis_alpha_os.product.report_view_model` over direct imports from v96/v99/v100/v104 report modules.
- Prefer `invis_alpha_os.product.portfolio_input` over direct imports from v98/v97/v95 portfolio-input modules.
- Prefer `invis_alpha_os.product.candidate_pipeline` over direct cross-version imports from v90/v91/v92/v93 modules.
- Do not migrate unrelated existing imports solely to use the facades.
- Add new behavior to the owning implementation module, not to a facade.

## Architecture Boundary

The facades must remain thin. If a facade starts owning calculations, validation rules, I/O, or orchestration, stop and
move that behavior to an implementation module. Common validation taxonomy remains a separate future decision.

## Verification Correction

- Cause: the initial facade-name test treated any `_v` substring as a version suffix and incorrectly matched
  `view_model`.
- Fix: detect only the actual version suffix pattern `_v` followed by digits.
- Verification: rerun focused, related, and full tests before PR creation.

## Explicit Non-Approval

- workflow change or manual workflow_dispatch: not approved / not executed
- provider live HTTP or market-data live fetch: not approved / not executed
- cache write or actual import: not approved / not executed
- broker API, broker login, raw broker export parsing, or raw Excel direct parsing: not approved / not executed
- raw broker/OHLCV/API persistence or reports-private raw data write: not approved / not executed
- env/secret display: not approved / not executed
- dependency / pyproject / Makefile change: not approved / not changed
- trading action, order placement, auto-trading, or real email: not approved / not executed

## Next Decision Point

After facade adoption is reviewed, consider a common validation taxonomy. Raw-input quarantine design and actual import
remain downstream and require separate approval.
