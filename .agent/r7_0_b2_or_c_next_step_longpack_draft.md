# R7.0-B2 vs R7.0-C — Next Step Longpack Draft (recommendation only)

**Date**: 2026-05-20 · **Based on**: [docs/84](../docs/84_r7_0_b1_jp_discovery_scanner_evaluation.md)

## Recommended path: **R7.0-B2 JP cache/universe expansion**

### Why B2 before C

- Local JP cache = **11 symbols** (watchlist-like); not full-market.
- `discover-jp` framework works; labels differentiate within cache (e.g. 5802 near_high + rapid_mover_20d).
- Insufficient-data ratio = 0% because missing names are simply absent from cache.
- Expanding universe/cache raises JP operator value before mirroring US scanner.

### B2 scope sketch (implementation Longpack later)

- Document target universe source (Prime subset fixture, expanded watchlist YAML, or ingested cache batch).
- Read-only ingest policy; no default enablement; no live HTTP without existing gates.
- Re-run B1 evaluation after breadth crosses a stated threshold (e.g. ≥50 symbols with min_bars).

### Alternative: R7.0-C US Universe Scanner MVP

- Proceed if US symmetry is higher priority and JP breadth deferred explicitly.
- Reuse R7.0-B patterns (`discover-us`, `local_cache_available_symbols`, same output contract).

## Safety (unchanged)

- No trading recommendations · no cache write by default · no Gmail in discovery MVP.
