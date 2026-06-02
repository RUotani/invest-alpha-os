# v92 Candidate Veto Rule Definition Pack Design

Date: 2026-06-02

## Decision

Record v92 as design-only while v91 Candidate Scoring Contract is still unmerged.

No v92 source implementation is added in this milestone. v92 should be a future separate source-only milestone after
v91 is reviewed.

## Purpose

v92 should structure veto rules that prevent candidate scores from being interpreted as action prompts when evidence,
portfolio constraints, financial quality, liquidity, valuation, or technical conditions are insufficient.

## Proposed Veto Keys

| Veto key | Purpose |
|---|---|
| `missing_evidence` | coverage, score detail, price, or source evidence is insufficient |
| `portfolio_constraint_breach` | candidate worsens cash shortage, individual-stock concentration, or equity overlap |
| `valuation_extreme` | valuation appears extreme relative to current evidence quality |
| `technical_overheat` | technical demand is strong but price/volume overheat is likely |
| `financial_quality_red_flag` | balance sheet, cash flow, debt, or accounting quality is weak |
| `liquidity_insufficient` | liquidity, volume, or tradability evidence is inadequate |
| `theme_only_hype` | theme fit is high but business/evidence quality is weak |
| `duplicate_exposure` | candidate duplicates existing index, sector, or theme risk |

## Relationship To v91

v91 exposes lightweight `veto_keys`:

- `blocked_missing_evidence`
- `blocked_portfolio_constraint`
- `blocked_financial_quality`

v92 should turn these into a richer rule contract with descriptions, required evidence, severity, next checks, and
safe report wording.

## Safety Boundary

This is design-only. No workflow change, provider access, market-data live fetch, cache write, actual import, broker
access, raw data parsing, env/secret display, email send, trading action, or order placement is approved.

## Next Step

Open a dedicated v92 source-only PR after v91 is reviewed or merged.
