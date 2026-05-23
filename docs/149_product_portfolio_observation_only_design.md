# Product — portfolio observation-only connection design

**Status**: design doc · no sizing defaults · observation only  
**Related**: `STATE.md` §1 portfolio, `portfolio/shadow_portfolio.py`

---

## Goal

Connect signals / observation_log / veto-at-t to portfolio **tracking** without implying trade recommendations or automated allocation.

## Current building blocks

| Component | Role |
| --- | --- |
| `ShadowPortfolioService` | JSONL shadow positions (manual / research tracking) |
| `observation_log.jsonl` | US signal rows + structured note (incl. veto-at-t) |
| Forward validation | Hit-rate / sample_quality for signal usefulness |
| peer_sync (new) | Relative peer divergence diagnostics |

## Design principles

1. **Observation-only labels** — reports say "shadow" / "tracked hypothesis", never "buy/sell/hold".
2. **Evidence linkage** — `ShadowPosition.thesis_evidence_ids` references observation row IDs or report paths (string IDs).
3. **No default sizing** — position `quantity` remains operator-entered; no auto `%` until `[要確認]` portfolio target is approved by human.
4. **Gates before sizing** — forward validation `sample_quality=usable` and veto join coverage are prerequisites for any future sizing module.
5. **Read-first CLI** — extend `snapshot shadow-portfolio` / future `portfolio summary` as read-only aggregations.

## Proposed flow (future, not implemented)

```text
weekly-us-observation → observation_log
validate us-forward-returns → sample_quality
validate peer-sync → divergence context
operator logs shadow position with thesis_evidence_ids
portfolio summary (read-only) → counts by theme / veto exposure
```

## Explicit non-goals

- Broker execution, rebalancing, or target weights
- Changing daily/signals defaults to show portfolio advice
- New `operator/` automation without explicit approval

## Human decisions required

- Portfolio progress % in `STATE.md` (currently `[要確認]%`)
- Whether shadow positions may reference live account symbols
- Minimum sample_quality before any sizing experiment

## Next implementation slice (when approved)

1. Read-only `portfolio observation-summary` CLI (counts + linked observation IDs) — **`snapshot portfolio-observation-summary`**
2. Schema doc for `thesis_evidence_ids` format
3. Optional weekly markdown appendix (opt-in flag)
