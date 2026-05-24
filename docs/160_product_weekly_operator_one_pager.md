# Product — 週次 ops コピペ one-pager

**Status**: operator copy-paste · read-first  
**Related**: [docs/150](./150_product_observation_log_weekly_runbook.md)

---

<<< COPY FROM HERE >>>

## 週次 ops（read-only · まずここ）

```bash
cd /path/to/invest-alpha-os
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate jp-peer-sync-readiness --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync --format markdown
```

## 週次蓄積（outputs 書込 · 人間承認後のみ）

```bash
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation \
  --manifest-out outputs/signals/weekly_us_manifest.json \
  --write-observation-log \
  --with-peer-sync \
  --format markdown
.venv/bin/python -m invis_alpha_os.cli.main log peer-sync-snapshot
```

## 事後サマリ（read-only）

```bash
.venv/bin/python -m invis_alpha_os.cli.main log us-signals-summary
.venv/bin/python -m invis_alpha_os.cli.main log peer-sync-summary
```

## 人間ゲート（本 one-pager では実行しない）

- tier-1 cache refresh / live HTTP → [docs/151](./151_product_p10_tier1_refresh_evidence_template.md)
- Gmail 配信 → 別 runbook
- `RULES.md` / portfolio 進捗 `[要確認]%` 更新

<<< COPY UNTIL HERE >>>
