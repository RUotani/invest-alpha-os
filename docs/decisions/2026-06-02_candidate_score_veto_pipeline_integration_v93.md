# v93 Candidate Score Veto Pipeline Integration Pack

Date: 2026-06-02

## Decision

Integrate v90 candidate pipeline traceability, v91 candidate scoring contract, and v92 candidate veto rules into a
single source-only / fixture-only weekly report view.

v93 adds an integrated assessment model and renders a short `Score / Veto` summary in the weekly candidate brief and
email preview. The output is a deep-dive prioritization and safety-check classification, not an execution signal.

## Preconditions

PR #450, `v92 Candidate Veto Rule Definition Pack`, is merged.

- merge commit: `59acce86805c483c2ff11286fd91a6c94ddb0812`
- v90 source: `weekly_candidate_pipeline_trace_v90.py`
- v91 source: `candidate_scoring_contract_v91.py`
- v92 source: `candidate_veto_rules_v92.py`

## Integration Contract

v93 connects:

- score band from v91
- hard / soft veto status from v92
- pipeline stage concepts from v90

Pipeline stages:

| Stage | Meaning |
|---|---|
| `coverage_missing` | reserved for future live/fixture universe integration |
| `score_blocked` | score band is blocked without hard veto |
| `veto_blocked` | hard veto exists |
| `watch` | monitor or additional-check candidate |
| `deep_dive` | deeper review candidate after soft-veto handling |
| `high_conviction_review` | high-priority review, not an execution instruction |

## Rule Mapping

- hard veto always maps to `veto_blocked`
- `BLOCKED` without hard veto maps to `score_blocked`
- `WATCH` maps to `watch`
- `DEEP_DIVE` with soft veto maps to `watch`
- `DEEP_DIVE` without veto maps to `deep_dive`
- `HIGH_CONVICTION_REVIEW` with hard veto maps to `veto_blocked`
- `HIGH_CONVICTION_REVIEW` with soft veto maps to `deep_dive`
- `HIGH_CONVICTION_REVIEW` without veto maps to `high_conviction_review`

## Weekly Report Boundary

Weekly Candidate Brief now includes a `Score / Veto 統合サマリー` section after the existing pipeline trace section.
Email preview includes only compact summary lines, not the long table.

The current v93 data is fixture/static only. Real symbol screening, live data, broker data, cache write, actual import,
and provider access remain outside this milestone.

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

After v93 review, decide whether v94 should expand fixture candidates by investment theme or whether v86 scheduled
run observation should take priority after `2026-06-06 07:30 JST`.
