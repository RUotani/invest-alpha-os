# Cursor longrun wave 8 — matched_normal + horizon export

## PRs

| PR | Theme | SHA |
| --- | --- | --- |
| #296 | `matched_normal` vs `rows_matched` fix + `validate p3-horizon-timeline` | `28af057` |

## Monitor

```bash
.venv/bin/python -m invis_alpha_os.cli.main validate p3-path-to-usable --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate p3-horizon-timeline --format json --horizon-rows 100
```

## P3 gate unchanged

- `matched_normal` still **1/10** toward usable; L1 blocked until ISO week rollover (`write_now_count=0`).
