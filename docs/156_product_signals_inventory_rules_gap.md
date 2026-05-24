# Product — signals inventory vs RULES.md §5 (Wave E)

**Status**: read-only inventory · 2026-05-24

---

## RULES.md §5 gate files

| Path (RULES) | Actual location | Status |
| --- | --- | --- |
| `signals/momentum.py` | `src/invis_alpha_os/signals/momentum.py` | **implemented** |
| `signals/peer_sync.py` | `src/invis_alpha_os/signals/peer_sync.py` | **implemented** (cache-only MVP) |
| `signals/veto_rules.py` | `src/invis_alpha_os/risk/veto_rules.py` | **implemented** (path drift) |

## Gap vs RULES wording

- veto lives under `risk/` not `signals/` — document only; no move without decision
- peer_sync JP peers need J-Quants loader (deferred)
- operator/ expansion still frozen per RULES until gates satisfied — **gates now satisfied for detection code existence**

## Observation-only helpers (main)

| Module | CLI entry |
| --- | --- |
| momentum | weekly-us-observation, daily `--us-momentum-section` |
| peer_sync | validate peer-sync, `--with-peer-sync` |
| veto | quality snapshot in weekly cycle |
| forward validation | validate us-forward-returns |
| portfolio | snapshot portfolio-observation-summary |
| health | snapshot observation-health |
| ops | validate ops-smoke |

## Recommended next (low-risk)

1. Merge open PR stack (#218 → #219 → #220)
2. Human: observation_log accumulation
3. Decision file to reconcile RULES §5 paths (optional)
