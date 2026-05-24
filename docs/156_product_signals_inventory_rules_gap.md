# Product — signals inventory vs RULES.md §5 (Wave E)

**Status**: read-only inventory · updated 2026-05-24

---

## RULES.md §5 gate files

| Path (RULES) | Actual location | Status |
| --- | --- | --- |
| `signals/momentum.py` | `src/invis_alpha_os/signals/momentum.py` | **implemented** |
| `signals/peer_sync.py` | `src/invis_alpha_os/signals/peer_sync.py` | **implemented** (US+JP cache) |
| `signals/veto_rules.py` | `src/invis_alpha_os/risk/veto_rules.py` | **implemented** (path drift) |

## Gap vs RULES wording

- veto lives under `risk/` not `signals/` — see [decision doc](../decisions/2026-05-24_rules_veto_path_documentation.md)
- JP peer_sync: cache loader + validate peer-sync wired (#226–227)
- operator/ expansion frozen per RULES

## Observation-only helpers (main)

| Module | CLI entry |
| --- | --- |
| momentum | weekly-us-observation, daily `--us-momentum-section` |
| peer_sync | validate peer-sync, `--with-peer-sync`, validate jp-peer-sync-readiness |
| veto | quality snapshot in weekly cycle |
| forward validation | validate us-forward-returns, peer-sync-forward-returns |
| portfolio | snapshot portfolio-observation-summary |
| health | snapshot observation-health |
| ops | validate ops-smoke (`--strict`) |

## Recommended next (low-risk)

1. P10 tier-1 cache refresh after human approval → forward matched without backtest
2. Continue weekly observation_log accumulation (docs/160)
3. Portfolio rubric acceptance → STATE % update (docs/154)
