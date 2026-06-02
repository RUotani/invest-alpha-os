# v91 Candidate Scoring Contract Design Pack

Date: 2026-06-02

## Decision

Add a source-only, fixture-only Candidate Scoring Contract for weekly candidate evaluation.

The contract defines seven evaluation axes, weighted scoring, normalized scoring, score bands, lightweight veto keys,
and fixture candidates. It is a contract for deep-dive prioritization, not a trading or execution system.

## Background

v90 added candidate pipeline traceability so the weekly report can explain where candidates drop out: coverage,
score, veto, or final candidate stage. The next missing layer is the scoring contract itself: what the candidate score
means, which axes are weighted, and how portfolio pressure and evidence quality affect review priority.

## Score Axes

| Axis | Weight | Meaning |
|---|---:|---|
| `theme_fit` | 1.2 | long-term theme fit |
| `business_momentum` | 1.3 | business, order, revenue, and margin momentum |
| `valuation_sanity` | 1.0 | initial valuation reasonableness |
| `technical_demand` | 0.8 | technical demand and price/volume support |
| `financial_quality` | 1.0 | balance sheet, FCF, debt, and accounting quality |
| `portfolio_fit` | 1.4 | fit with cash, individual-stock, and equity exposure constraints |
| `evidence_quality` | 1.3 | quality and quantity of supporting evidence |

The heavier weights on `portfolio_fit` and `evidence_quality` reflect the current v78/v82 context:

- cash: `508.2万円 / 11.7%`
- individual stocks: `846.3万円 / 19.6%`
- equity total: `2,934.5万円 / 67.8%`

## Score Bands

| Band | Rule | Meaning |
|---|---|---|
| `BLOCKED` | normalized score `<45`, or hard evidence / portfolio / financial constraint | evidence or constraints must be reviewed before deeper work |
| `WATCH` | `45 <= score < 65` | monitor candidate |
| `DEEP_DIVE` | `65 <= score < 80`, evidence quality `>=3`, portfolio fit `>=2` | deeper review candidate |
| `HIGH_CONVICTION_REVIEW` | score `>=80`, evidence quality `>=4`, portfolio fit `>=3` | high-priority review, not an execution instruction |

## Lightweight Veto Keys

v91 does not implement the full veto rule engine. It only exposes lightweight veto keys so v92 can build on the
contract:

- `blocked_missing_evidence`: `evidence_quality <= 1`
- `blocked_portfolio_constraint`: `portfolio_fit <= 1`
- `blocked_financial_quality`: `financial_quality <= 1`

## Fixture Candidates

The fixture candidates are intentionally fictional:

- `GRID_A`
- `ROBO_B`
- `MAT_C`
- `CASH_D`
- `HYPE_E`

They are designed to verify blocked, watch/deep-dive, and high-priority review behavior without touching live data or
real broker/position data.

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
- automated execution or email send

## Next Decision Point

After v91 review, define v92 veto rules as a separate source-only milestone. v92 should structure missing evidence,
portfolio constraint breach, valuation extreme, technical overheat, financial quality red flag, liquidity
insufficiency, theme-only hype, and duplicate exposure into explicit veto rules.
