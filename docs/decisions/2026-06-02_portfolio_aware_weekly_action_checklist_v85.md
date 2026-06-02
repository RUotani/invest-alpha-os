# Portfolio-Aware Weekly Action Checklist v85

Date: 2026-06-02

## Decision

Add a portfolio-aware weekly action checklist to the Weekly Candidate Brief copy-ready report and email preview.

The checklist converts the v81 readable weekly report into a weekly operating view with three explicit buckets:

- 今週やってよいこと
- 今週やらないこと
- 次に確認すること

## Background

v79 confirmed that the scheduled weekly candidate brief workflow can generate and publish an artifact, but the artifact
was not sufficient as an investment decision-support report when candidate count was zero. v80 recorded that quality
gap as a review-only finding. v81 improved the zero-candidate UX by adding a weekly conclusion, portfolio context,
action classification, Do / Don't, and ChatGPT review request.

v85 goes one step further: the weekly report should make the next safe human action clear even when there are no strong
new-risk candidates.

## Portfolio Context Used

The checklist uses only the v78 redacted monthly portfolio context:

- total assets: approximately `4,327.9万円`
- cash: `508.2万円 / 11.7%`
- individual stocks: `846.3万円 / 19.6%`
- equity total: `2,934.5万円 / 67.8%`
- bonds: `582.7万円 / 13.5%`
- gold: `234.5万円 / 5.4%`
- crypto/high-beta proxy: `57.5万円 / 1.3%`
- leveraged exposure: `10.5万円 / 0.2%`

No raw broker export, raw Excel file, broker API, market live fetch, cache write, or actual import is used.

## What Changed

- The copy-ready Weekly Candidate Brief now includes `## 今週の行動チェックリスト`.
- The checklist always appears, including candidate-zero reports.
- The checklist links candidate-zero output to cash shortage, individual-stock pressure, equity exposure, data quality,
  and next-review tasks.
- The existing action classification now points more directly to suppression, monitoring, cleanup review, and data
  quality review.
- The email text and HTML preview include a compact mobile-readable action checklist.

## Interpretation

Candidate zero is not treated as a report failure. Under cash `11.7%`, individual stocks `19.6%`, and equity total
`67.8%`, candidate zero is treated as a valid suppression signal:

- avoid adding weakly supported new risk
- prefer monitoring, cleanup review, and cash recovery
- check coverage, score details, veto reasons, and overlapping exposure before deeper review

## Safety Boundary

This milestone is source-only and observation-only.

Explicitly not approved:

- provider live access
- market-data live HTTP
- Tiingo / Stooq / Yahoo / Polygon live fetch
- cache write or cache directory creation
- actual refresh/import
- manual actual import
- broker API access or broker login
- raw broker export parsing
- raw broker data persistence
- raw OHLCV/API persistence
- raw Excel direct parsing
- reports-private raw data write
- Git-tracked raw data write
- env/secret display
- dependency / pyproject changes
- workflow direct changes or `.github/workflows` changes
- trading action or order placement
- automated buy/sell execution recommendation

## Known Limits

- The checklist uses a fixed redacted v78 context until a future approved monthly snapshot update is provided.
- It does not compute target allocation gaps dynamically.
- It does not score cleanup candidates beyond the current observation-only weekly candidate brief structure.
- It does not approve cache write, actual import, provider access, broker access, or trading actions.

## Next Candidates

1. v82 Target Allocation Gap Calculator
2. v83 Cleanup Priority Scoring Pack
3. Scheduled weekly run observation after the next Saturday JST workflow execution
