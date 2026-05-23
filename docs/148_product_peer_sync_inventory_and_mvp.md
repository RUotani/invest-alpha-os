# Product — peer_sync inventory and cache-only MVP

**Status**: implemented (cache-only) · observation only  
**Related**: `docs/decisions/2026-05-24_peer_sync_cache_only_mvp.md`, `STATE.md` §7

---

## Inventory (2026-05-24)

| Item | Status | Notes |
| --- | --- | --- |
| `signals/peer_sync.py` | **added** | Anchor→peer return spread + rolling correlation |
| `config/peer_map.yaml` | exists | AAPL→MSFT/GOOGL; JP codes 7011→7012/7013 |
| `discovery/cross_market_contract.py` | exists | JP/US universe merge — **not** peer_sync |
| `operator/runner.py` cross_market | exists | Ops path; frozen for new features |
| Weekly observation cycle | **opt-in** | `--with-peer-sync` on weekly-us-observation |
| RULES.md §5 | note | Lists `signals/veto_rules.py` but veto lives under `risk/` (known drift) |

## MVP behavior

- Read `peer_map.yaml`, load US cache bars via `try_load_cached_us_daily_bars`
- Classify each edge: `in_sync`, `diverged_anchor_outperform`, `diverged_peer_outperform`, `insufficient_data`, `missing_cache`
- No HTTP, no cache write, no trade language

## Commands

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format json --window-days 20
```

## Out of scope (this sprint)

- JP daily bars peer_sync (J-Quants cache alignment TBD)
- observation_log append for peer_sync rows
- operator-runner integration

## Weekly integration

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync
```
