# Product P2 — MSFT / AAPL cache refresh evidence pack

**Date**: 2026-05-23 (JST)  
**Base**: `origin/main` @ `deb1599` (PR #206 runbook merged) · P1 @ `6185b95`  
**Nature**: **docs-only** evidence — no cache JSON in git · no full operator logs in git

---

## 1. Purpose

Record that P2 **MSFT / AAPL** on-disk caches were refreshed with **valid ascending daily bars**, restoring **16/16** US watchlist parse for cache-only momentum and US signals dry-run.

Observation only — not buy/sell advice.

---

## 2. Preflight (agent, 2026-05-23)

| Check | Result |
|-------|--------|
| `origin/main` | `deb1599` |
| Working tree | clean |
| Open product PRs | #207 (P2b observation + AAPL fixture code) — separate from this evidence pack |
| Live HTTP / cache write in this PR | **none** (refresh already done under operator gates) |

---

## 3. Refresh execution (operator — not re-run by this PR)

| Symbol | Path | Gate / source | Evidence on disk |
|--------|------|---------------|------------------|
| **MSFT** | `outputs/market_data/us_daily_bars/MSFT.json` | `local_fixture` import · **no HTTP** | `outputs/operator/p2_cache_refresh_20260523T223659.log` |
| **AAPL** | `outputs/market_data/us_daily_bars/AAPL.json` | `stooq_preview` · gated live + write | `outputs/operator/p2_aapl_refresh_20260523T223801.log` |

**MSFT** (from operator log summary): dry-run `bar_count=72` → write `status=success` → preview `validation_status=ok`.

**AAPL** (from operator log summary): live preview `row_count=10508` → write `cache_write_performed=true` → preview `validation_status=ok`.

Secrets and `.env` contents are **not** copied into this document.

---

## 4. Post-refresh verification (agent read-only, 2026-05-23)

### 4.1 Per-symbol cache preview

| Symbol | validation_status | source | bar_count | first_date | last_date |
|--------|-------------------|--------|-----------|------------|-----------|
| MSFT | ok | local_fixture | 72 | 2024-01-02 | 2024-04-10 |
| AAPL | ok | stooq_preview_gated_live | 10508 | 1984-09-07 | 2026-05-22 |

Commands:

```bash
.venv/bin/python -m invis_alpha_os.cli.main debug us-daily-bars-cache-preview \
  --path outputs/market_data/us_daily_bars/MSFT.json --symbol MSFT
.venv/bin/python -m invis_alpha_os.cli.main debug us-daily-bars-cache-preview \
  --path outputs/market_data/us_daily_bars/AAPL.json --symbol AAPL
```

### 4.2 US signals + momentum (16 watchlist)

| Metric | Before P2 (P1 smoke) | After P2 refresh |
|--------|----------------------|----------------|
| US signals dry-run ok | 14/16 | **16/16** |
| parse_failed symbols | MSFT, AAPL | **none** |
| Momentum load (cache) | 14/16 | **16/16** |
| `build_momentum_signals` ranked | 14 | **16** |

Verification used explicit manifest under `outputs/signals/p1_us_16_cache_manifest.json` (local only, **not committed**) and `build_us_cache_signals_previews_from_batch_manifest`.

### 4.3 P1 daily smoke (read-only report)

```bash
.venv/bin/python -m invis_alpha_os.cli.main daily \
  --us-signals-dry-run-manifest outputs/signals/p1_us_16_cache_manifest.json \
  --us-cache-preview \
  --us-momentum-section
```

Report path (local): `outputs/reports/daily/<today_jst>.md` — includes US Signals Dry Run, US Cache Preview, US Momentum sections when flags set.

---

## 5. P2 outcome

| Goal | Status |
|------|--------|
| MSFT invalid stub dates removed | **done** |
| AAPL invalid stub dates removed | **done** |
| 16/16 cache-only signals | **done** |
| 16/16 momentum from cache | **done** |
| P1 end-to-end smoke green | **done** (operator + agent read-only confirm) |

---

## 6. Follow-ups (not this PR)

| Item | Track |
|------|--------|
| `observation_log` batch CLI | PR **#207** (`log us-signals-batch`, `daily --write-observation-log`) |
| P3 JP Core50 cache | [docs/136](./136_r7_0_product_pivot_signals_pack.md) |
| P4 weekly observation cycle | docs/136 P4 |
| Ops wave runner / prepare-next | **frozen** |

---

## 7. References

- Runbook: [docs/138](./138_product_p2_msft_aapl_cache_refresh.md)
- P1 smoke: [docs/137](./137_product_p1_us_signals_cache_smoke.md)
- Product pivot: [docs/136](./136_r7_0_product_pivot_signals_pack.md)
