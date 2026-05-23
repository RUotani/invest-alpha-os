# Product P1 — US signals cache-only end-to-end smoke

**Date**: 2026-05-23  
**Base**: `origin/main` @ `4442b7f` (CI success)  
**Branch**: `work/product-p1-us-signals-cache-smoke`

## Goal

US 16 watchlist symbols → cache-only reads → momentum → veto → daily report → observation-only output.  
No live HTTP, no cache write, no Gmail.

## Preconditions

- `outputs/market_data/us_daily_bars/*.json` present (16 files on smoke host)
- `.venv` activated

## Smoke commands

```bash
git fetch origin main
git rev-parse origin/main   # expect 4442b7f or later

# 1) Watchlist (no HTTP)
.venv/bin/python -m invis_alpha_os.cli.main us-watchlist-preview

# 2) Explicit batch manifest (no directory scan)
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from invis_alpha_os.config.us_watchlist import load_us_watchlist_tickers
root = Path(".")
entries = [
    {"symbol": s, "cache_path": f"outputs/market_data/us_daily_bars/{s}.json"}
    for s in load_us_watchlist_tickers()
    if (root / "outputs/market_data/us_daily_bars" / f"{s}.json").is_file()
]
out = root / "outputs/signals/p1_us_16_cache_manifest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"schema_version": 1, "source": "product-p1-smoke", "entries": entries}, indent=2))
print(f"wrote {out} entries={len(entries)}")
PY

# 3) Daily report (observation-only sections; defaults unchanged)
.venv/bin/python -m invis_alpha_os.cli.main daily \
  --us-signals-dry-run-manifest outputs/signals/p1_us_16_cache_manifest.json \
  --us-cache-preview \
  --us-momentum-section
```

Report path: `outputs/reports/daily/<today_jst>.md`

## Smoke results (2026-05-23 host)

| Step | Result |
|------|--------|
| Watchlist symbols | 16 |
| Cache JSON files | 16 |
| US signals dry-run (`status=ok`) | 14 ok, 2 invalid (`parse_failed`) |
| US cache preview rows | 16 (MSFT/AAPL note: `parse_failed`) |
| US momentum ranked | 14 (MSFT, AAPL skipped — invalid bar dates) |
| Veto triggered | 0 |
| Report sections | JP momentum (config on), US dry-run, US cache preview, US momentum (CLI opt-in) |

### Parse failures (data gap, not missing code)

`MSFT.json` / `AAPL.json` use monthly stub dates with duplicates and non-ascending order → `parse_us_daily_bars_payload` correctly rejects (`_us_daily_bar_rows_valid`).

**Fix path**: re-ingest with sanitized daily bars (gated cache write / batch import) — out of scope for read-only smoke.

## Pipeline map

| Stage | Module / CLI |
|-------|----------------|
| US cache read | `us_daily_bars_cache`, `us_cache_signals` |
| Momentum | `signals.momentum`, `render_us_momentum_cache_only_section` |
| Veto | `risk.veto_rules` (`build_momentum_veto_result`) |
| Report | `cli daily` + `--us-signals-dry-run-manifest` / `--us-cache-preview` / `--us-momentum-section` |
| Observation | `observation_only` flags in JSON; `outputs/reports/daily/*.md` |

## Tests

```bash
git diff --check
pytest -q tests/test_us_cache_signals.py tests/test_us_momentum_daily.py \
  tests/test_us_signals_report_dry_run.py tests/test_us_cache_signals_batch_manifest.py
pytest -q tests   # full suite before PR
```

## Next implementation (P1 follow-up)

1. **Refresh MSFT/AAPL cache** — see **[docs/138](./138_product_p2_msft_aapl_cache_refresh.md)** (P2; gated ingest, separate PR).
2. **observation_log** — [docs/140](./140_product_p2b_observation_log.md) (`log us-signals-batch` / `daily --write-observation-log`; opt-in).
3. Optional: `include_us_momentum_cache_only_section` in `market_data.yaml` after 16/16 parse green (config opt-in; default stays off).
