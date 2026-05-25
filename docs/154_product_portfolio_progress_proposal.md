# Product — portfolio observation progress proposal (Wave C)

**Status**: readiness rubric · `[要確認]%` unchanged until human acceptance

---

## Current capabilities

- `snapshot portfolio-observation-summary` — linkage + **by_symbol** / **by_tag** exposure counts
- Shadow positions remain manual; no sizing defaults
- Malformed JSONL rows skipped (read-only)

## Readiness rubric (observation only)

| ID | Milestone | Acceptance criteria | Auto-check |
| --- | --- | --- | --- |
| P0 | Shadow JSONL + CLI | `snapshot portfolio-observation-summary` exit 0 | yes |
| P1 | Observation linkage | `positions_with_resolved_links` > 0 when shadow has thesis/evidence | read-only summary |
| P2 | Weekly log sustained | `us_signal_rows` grows week-over-week (human `--write-observation-log`) | observation-health |
| P3 | Forward usable | `validate us-forward-returns` → `sample_quality=usable` **without** `--backtest-within-cache` | forward validation |
| P4 | Sizing experiment | Explicit human approval + separate design doc | **not started** |

## Suggested STATE mapping (human approval required)

| Accepted through | Suggested portfolio % |
| --- | ---: |
| P0 only | 25% |
| P0 + P1 | 40% |
| P0–P2 | 55% |
| P0–P3 | 70% |
| P4 approved | TBD |

**Do not auto-update STATE %** until operator confirms the rubric above.

## Shadow seed (P1)

See [docs/165](./165_product_shadow_portfolio_seed.md) and `config/examples/shadow_portfolio_positions.example.jsonl`.

## Read-only commands

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown --strict
```

**Auto-evaluator (read-only)**: `snapshot observation-health` includes `portfolio.readiness` (P0–P3 milestones, `suggested_percent` only — STATE % remains locked until human acceptance).

## Out of scope

- Buy/sell recommendations
- Default position sizing
- Live HTTP / cache write
