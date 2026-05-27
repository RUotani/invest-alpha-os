# Weekly Observation Report v1

Observation only — not buy/sell advice.
Report date: **2026-05-27**

## Executive summary

- US signals ok: **16/16** · veto triggered (cache batch): **0**
- observation_log us_signal_rows: **432** · repeat symbols: **16**
- P3 matched_normal: **1/10** (monitoring; not short-term dev KPI)

---


## US signals (cache-only cycle)

Observation only — not buy/sell advice.

## Manifest
- entries: 16
- missing cache on watchlist: 0

## Signals batch
- status: ok
- previews: 16

## Quality snapshot
- signals ok: 16/16
- veto triggered: 0
- portfolio_exposure: 2 shadow position(s); veto_triggered=0, no_veto=2, signal_unknown=0 · detail: snapshot portfolio-exposure-by-signal-veto --format markdown

## Duplicate ISO-week write preflight (read-only)

- would_duplicate_count: 16
- would_new_symbol_week_count: 0
- recommendation: Skip re-logging symbols whose ISO week already exists in observation_log; prefer one row per symbol per ISO week for P3 forward validation.
- MSFT 2026-W22: 1 existing rows (event=2026-05-26)
- NVDA 2026-W22: 1 existing rows (event=2026-05-26)
- AAPL 2026-W22: 1 existing rows (event=2026-05-26)
- AMZN 2026-W22: 1 existing rows (event=2026-05-26)
- GOOGL 2026-W22: 1 existing rows (event=2026-05-26)
- META 2026-W22: 1 existing rows (event=2026-05-26)
- TSLA 2026-W22: 1 existing rows (event=2026-05-26)
- GLDM 2026-W22: 1 existing rows (event=2026-05-26)
- SLV 2026-W21: 27 existing rows (event=2026-05-18)
- TLT 2026-W21: 27 existing rows (event=2026-05-18)
- TMF 2026-W21: 27 existing rows (event=2026-05-18)
- SPY 2026-W21: 27 existing rows (event=2026-05-18)
- QQQ 2026-W21: 27 existing rows (event=2026-05-18)
- MSTR 2026-W21: 27 existing rows (event=2026-05-18)
- COIN 2026-W21: 27 existing rows (event=2026-05-18)
- MARA 2026-W21: 27 existing rows (event=2026-05-18)

- earliest_next_iso_week_start: 2026-05-25
- days_until_earliest_rollover: 0
- days_until_earliest_rollover_note: 0 = earliest_next_iso_week_start reached or passed (calendar rollover date elapsed; write_now may still be 0 if cache/as_of has not advanced)
- rollover_passed_write_still_blocked: planned writes still duplicate or cache/as_of not advanced
- l1_unblock_hint: ISO week rollover date has passed but write_now_count=0: planned writes still duplicate existing symbol×ISO week rows or cache/as_of has not advanced; refresh P10 tier-1 cache and re-check write_now_count

## P3 path preflight (read-only)

- P3 path: matched=1/10 need=9; dominant=rollover_passed_cache_or_duplicate_blocked; path_a_pending=16 path_b_write_now=0
- dominant_path: rollover_passed_cache_or_duplicate_blocked
- matched_normal: 1 (rows_matched_all: 20)
- samples_needed_for_usable: 9
- path_a pending_horizon_rows: 16
- path_b write_now_count: 0 l1_status=blocked_duplicate_iso_week

### Suggested next steps
- ISO week rollover date has passed but write_now_count=0: planned writes still duplicate existing symbol×ISO week rows or cache/as_of has not advanced; refresh P10 tier-1 cache and re-check write_now_count
- Wait for cache horizon on existing log rows; re-run validate forward-p3-status weekly

## Observation log
- us_signal_rows: 432
- observation_log_total_lines: 538
- by_status: {'ok': 432}
- signal aging (days, avg/max): 1.5555555555555556 / 3
- repeat signal symbols: AAPL, AMZN, COIN, GLDM, GOOGL, MARA, META, MSFT, MSTR, NVDA, QQQ, SLV, SPY, TLT, TMF, TSLA

## Next research checklist (observe only)
- [repeat_signal] AAPL: multiple US signal observations logged for symbol → review note history and momentum label changes
- [repeat_signal] AMZN: multiple US signal observations logged for symbol → review note history and momentum label changes
- [repeat_signal] COIN: multiple US signal observations logged for symbol → review note history and momentum label changes
- [repeat_signal] GLDM: multiple US signal observations logged for symbol → review note history and momentum label changes
- [repeat_signal] GOOGL: multiple US signal observations logged for symbol → review note history and momentum label changes
- [repeat_signal] MARA: multiple US signal observations logged for symbol → review note history and momentum label changes
- [repeat_signal] META: multiple US signal observations logged for symbol → review note history and momentum label changes
- [repeat_signal] MSFT: multiple US signal observations logged for symbol → review note history and momentum label changes
- [us_forward_partial] —: US forward P3 1/10 toward usable (matched_normal=1); rows_matched_all=20 (supplementary); log_lines=538 skip_pattern=none (docs/161) → validate forward-p3-status; accumulate toward 10 matched
- [peer_forward_usable] —: matched rows sufficient for exploratory bucket review → validate peer-sync-forward-returns --format markdown

## Forward validation summary
- rows_matched (all): 20
- matched_normal (P3): 1
- all_rows_sample_quality: usable (supplementary)
- p3_sample_quality: thin
- interpretation: Review hit-rate buckets as observation-only diagnostics.
- samples_needed_for_usable: 9
- p3_progress: 1/10 toward usable

## US forward resolution breakdown
- Need 0 more matched rows; stale_skips=8 insufficient_future=404 (share=94% of US resolutions) (docs/161)
- insufficient_future_share: 0.9352
- backtest_within_cache_matched (exploratory): 432 — Exploratory upper bound only — not P3 milestone (docs/161 opt-in backtest)
- peer_sync_forward: matched=52 quality=usable
- peer_sync_p3_progress: usable (52 matched)

### Suggested next commands
- `.venv/bin/python -m invis_alpha_os.cli.main validate p3-path-to-usable --format markdown`
- `.venv/bin/python -m invis_alpha_os.cli.main validate p3-horizon-timeline --format json --horizon-rows 100`
- `.venv/bin/python -m invis_alpha_os.cli.main validate forward-p3-status --format markdown`
- `.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown`
- `.venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary`
- `.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --format markdown`
- veto-at-t status: joined
- 5d: hit_rate_positive=0.7 (n=20)
- 20d: hit_rate_positive=0.0 (n=3)
- 60d: hit_rate_positive=1.0 (n=3)

## Peer sync (cache-only)
- pairs evaluated: 4
- `diverged_anchor_outperform`: 1
- `diverged_peer_outperform`: 1
- `insufficient_data`: 2

### Diverged pairs (observe only)
- AAPL vs MSFT: diverged_anchor_outperform (spread 17.26%)
- AAPL vs GOOGL: diverged_peer_outperform (spread 4.22%)

## Ops smoke (read-only)
- `validate ops-smoke --format markdown`
- `snapshot observation-health --format json`

## Operator one-pager (docs/160)
- Weekly copy-paste: `docs/160_product_weekly_operator_one_pager.md`
- Evidence manifest: `.venv/bin/python -m invis_alpha_os.cli.main log evidence-manifest --task-id weekly_preflight_YYYYMMDD --report-date YYYY-MM-DD`


## Risk veto (observation log; read-only)

- 0/432 US signal log rows with veto_triggered=true
- status: ok
- veto_triggered_rows: 0
- veto_triggered_share: 0.0

## Portfolio observation

- shadow_positions: 2
- symbols_with_signal_context: 16
- human_accepted_percent: 55
- rubric_tier: P0-P2 (P0 through P2 (weekly sustained))
- P0: passed — portfolio-observation-summary builds successfully
- P1: passed — evidence_ids=2 resolved_links=2
- P2: passed — weekly_trend=growing delta=336
- P3: blocked — p3_sample_quality=thin matched_normal=1/10 (rows_matched_all=20; all_rows_sample_quality=usable); matched rows sufficient for exploratory bucket review; skip_pattern=none; peer_sync_forward usable (52 matched, US P3 milestone separate — docs/154); normal matched=1/10; dominant_category=duplicate_same_week_rows; backtest_exploratory=432 (not P3 milestone); l1_status=blocked_duplicate_iso_week; iso_rollover_in_days=0 earliest=2026-05-25; p3_path=rollover_passed_cache_or_duplicate_blocked
- portfolio_p3_forward: 1/10 toward usable

## P10 gap (cache / tier-1; gated refresh)

- tier_1_missing_count: 0
- stale_skip_symbols: SLV, TLT, TMF, SPY, QQQ, MSTR
- stale_skip_count: 8
- note: P10 tier-1 cache refresh requires human chat approval (docs/162); no live HTTP in v1 report.

## P3 live forward usable (time-dependent monitoring gate)

- **P3 live forward usable is a time-dependent monitoring gate — not a short-term development KPI.**
- status: `immature_monitoring` (immature but monitoring — not a coding completion blocker)
- matched_normal: 1/10 (thin)
- samples_needed_for_usable: 9
- portfolio_readiness: Portfolio observation milestones (P0–P2) are evaluated independently; P3 live forward usable maturity does not block Weekly Observation Report v1.
- historical_backfill: deferred — not in scope for v1 completion

## Next human actions

- Forward P3: 1/10 matched; ~9 more rows toward usable (weekly accumulation)
- .venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
- .venv/bin/python -m invis_alpha_os.cli.main validate post-refresh-smoke --format markdown
- Peer-sync forward: usable (52 matched)
- Historical stale skips may persist in log: SLV(1), TLT(1), TMF(1), SPY(1), QQQ(1), MSTR(1) (docs/161; new writes use fresh cache)
- ISO week rollover date has passed but write_now_count=0: planned writes still duplicate existing symbol×ISO week rows or cache/as_of has not advanced; refresh P10 tier-1 cache and re-check write_now_count
- Wait for cache horizon on existing log rows; re-run validate forward-p3-status weekly
- [repeat_signal] AAPL: review note history and momentum label changes
- [repeat_signal] AMZN: review note history and momentum label changes
- [repeat_signal] COIN: review note history and momentum label changes
- [repeat_signal] GLDM: review note history and momentum label changes
- [repeat_signal] GOOGL: review note history and momentum label changes
- … +5 more (see observation-health / p3-path-to-usable)

## Report command

- `.venv/bin/python -m invis_alpha_os.cli.main weekly-observation-report-v1`
