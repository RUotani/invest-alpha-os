# Cursor longrun wave 7 — validate p3-path-to-usable

## PR

- **#293** merged @ `f1cfe67`

## Deliverable

- `validate p3-path-to-usable` — path A/B + `p3_horizon_timeline` with `--horizon-rows` (default 50)
- `build_p3_path_to_usable_bundle` — fallback path synthesis when stall/summary absent
- ops-smoke / forward_validation next_commands updated

## Monitor

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate p3-path-to-usable --format markdown
```

## P3 unchanged

- US normal matched still thin vs usable (10); dominant path remains horizon + ISO week rollover per local run.
