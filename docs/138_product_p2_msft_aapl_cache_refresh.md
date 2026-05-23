# Product P2 — MSFT / AAPL cache refresh (gated ingest)

**Date**: 2026-05-23  
**Depends on**: Product P1 merged (`6185b95`) — 14/16 US symbols parse; **MSFT** / **AAPL** invalid (monthly stub dates).  
**Branch**: `work/product-p2-msft-aapl-cache-refresh`
**Evidence (refresh complete)**: [docs/139](./139_product_p2_msft_aapl_evidence_pack.md) — 16/16 parse, operator logs under `outputs/operator/` (not in git).

## Goal

Replace invalid `outputs/market_data/us_daily_bars/{MSFT,AAPL}.json` with **schema v1** envelopes: ascending unique daily `bars[]`, so momentum / US signals dry-run reach **16/16**.

## Hard rules

- **No** unattended live HTTP or cache write.
- **No** Makefile / workflow / `pyproject.toml` changes.
- **Do not commit** `outputs/market_data/us_daily_bars/*.json`.
- Observation-only downstream; no buy/sell wording.

## Path A — MSFT (no HTTP, recommended first)

Repo fixture: `tests/fixtures/us_daily_bars/MSFT.json` (72 ascending daily rows).

```bash
# 1) Dry-run (default)
.venv/bin/python -m invis_alpha_os.cli.main debug us-daily-bars-cache-import \
  --symbol MSFT \
  --bars-file tests/fixtures/us_daily_bars/MSFT.json \
  --asset-class us_equity \
  --source local_fixture

# 2) Write (operator explicit; no Stooq HTTP)
.venv/bin/python -m invis_alpha_os.cli.main debug us-daily-bars-cache-import \
  --symbol MSFT \
  --bars-file tests/fixtures/us_daily_bars/MSFT.json \
  --asset-class us_equity \
  --source local_fixture \
  --write-cache

# 3) Verify parse
.venv/bin/python -m invis_alpha_os.cli.main debug us-daily-bars-cache-preview \
  --path outputs/market_data/us_daily_bars/MSFT.json --symbol MSFT
```

## Path B — AAPL (gated Stooq live, one symbol at a time)

No committed AAPL bars fixture today. Use existing **single-symbol** Stooq path (see `docs/56`, `docs/11`).

```bash
# 1) Live shape + parse preview (requires HTTP gate)
CONFIRM_US_LIVE_HTTP=YES .venv/bin/python -m invis_alpha_os.cli.main \
  debug us-provider-cache-preview --symbol AAPL --provider stooq_preview --live

# 2) Persist only after preview_ok (cache write gate)
CONFIRM_US_LIVE_HTTP=YES CONFIRM_US_CACHE_WRITE=YES .venv/bin/python -m invis_alpha_os.cli.main \
  debug us-provider-cache-preview --symbol AAPL --provider stooq_preview --live --write-cache

# 3) Verify
.venv/bin/python -m invis_alpha_os.cli.main debug us-daily-bars-cache-preview \
  --path outputs/market_data/us_daily_bars/AAPL.json --symbol AAPL
```

**Alternative (no HTTP)**: add `tests/fixtures/us_daily_bars/AAPL.json` (valid ascending array) in a follow-up PR, then use Path A import.

## Post-refresh smoke (read-only)

```bash
.venv/bin/python -m invis_alpha_os.cli.main daily \
  --us-signals-dry-run-manifest outputs/signals/p1_us_16_cache_manifest.json \
  --us-cache-preview \
  --us-momentum-section
```

Expect: US signals dry-run **16/16 ok**, momentum ranked **16**, MSFT/AAPL rows in tables.

## PR boundary

| In scope | Out of scope |
|----------|----------------|
| Runbook (this doc) | Ops wave runner / prepare-next |
| Optional AAPL fixture PR | Batch unattended ingest |
| Operator-executed refresh | Changing `daily_report` defaults |
