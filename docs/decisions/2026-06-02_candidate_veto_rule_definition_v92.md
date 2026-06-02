# v92 Candidate Veto Rule Definition Pack

Date: 2026-06-02

## Decision

Add a source-only, fixture-only Candidate Veto Rule contract on top of the merged v91 Candidate Scoring Contract.

v92 turns the lightweight v91 veto keys into explicit rule definitions with severity, Japanese explanation, and next
check wording. The contract is designed to suppress hype, overheating, evidence gaps, portfolio constraint breaches,
financial red flags, liquidity gaps, and duplicate exposure before candidate scores are interpreted too strongly.

## Preconditions

PR #449, `v91 Candidate Scoring Contract Design Pack`, is merged.

- merge commit: `80f5f1c0d0791ab4ebc63ddd027af0a953f21d79`
- v91 source file: `src/invis_alpha_os/product/candidate_scoring_contract_v91.py`

## Rule Contract

| Veto key | Severity | Trigger |
|---|---|---|
| `missing_evidence` | HARD | `evidence_quality <= 1` |
| `portfolio_constraint_breach` | HARD | `portfolio_fit <= 1` |
| `valuation_extreme` | SOFT or HARD | `valuation_sanity <= 1`; escalates to HARD when `technical_demand >= 4` |
| `technical_overheat` | SOFT | `technical_demand >= 5 and valuation_sanity <= 2` |
| `financial_quality_red_flag` | HARD | `financial_quality <= 1` |
| `liquidity_insufficient` | SOFT | `liquidity_score is not None and liquidity_score <= 1` |
| `theme_only_hype` | SOFT | `theme_fit >= 4 and evidence_quality <= 2 and business_momentum <= 2` |
| `duplicate_exposure` | SOFT | `duplicate_exposure is True` |

## Severity Meaning

- `HARD`: stop before deeper review until evidence or constraint is resolved by human review.
- `SOFT`: suppress priority until the next check is complete.
- `INFO`: reserved for future explanatory output; v92 does not auto-emit INFO reasons.

## v91 Integration Boundary

v92 adds `veto_input_from_score_result(...)` so a v91 `CandidateScoreResult` can be converted into v92 veto input
without importing v92 from v91. This avoids circular imports and keeps v92 independent from weekly report integration.

Weekly report integration is intentionally deferred to a future PR. v92 only defines the contract, renderer, and tests.

## Safety Boundary

Explicitly not approved:

- workflow changes or `.github/workflows` changes
- manual workflow dispatch
- provider live HTTP or market-data live fetch
- cache write or cache directory creation
- actual refresh/import or manual actual import
- broker API access or broker login
- raw broker export parsing
- raw broker data persistence
- raw OHLCV/API persistence
- raw Excel direct parsing
- reports-private raw data write
- Git-tracked raw data write
- env/secret display
- dependency / pyproject / Makefile changes
- trading action or order placement
- automated execution or real email send

## Next Decision Point

After v92 review, decide whether v93 should integrate veto reason rendering into the weekly candidate brief, or first
add fixture-level candidate scoring and veto summaries to a report-only context pack.
