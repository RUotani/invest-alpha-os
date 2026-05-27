# Cursor longrun wave 9 — weekly P3 preflight

## PRs

| PR | Theme | SHA |
| --- | --- | --- |
| #299 | `build_weekly_p3_path_preflight` + `p3_monitoring_next_commands()` | `e2bc4e1` |

## Monitor

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --format markdown
```

Markdown includes **Duplicate ISO-week** and **P3 path preflight** sections when observation_log exists.

## P3 gate unchanged

- `matched_normal` still thin vs usable; L1 when `write_now_count > 0` after ISO week rollover.
