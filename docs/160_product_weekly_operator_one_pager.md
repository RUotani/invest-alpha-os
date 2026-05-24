# Product — 週次 ops コピペ one-pager

**Status**: operator copy-paste · read-first  
**Related**: [docs/150](./150_product_observation_log_weekly_runbook.md), [docs/154](./154_product_portfolio_progress_proposal.md), [docs/151](./151_product_p10_tier1_refresh_evidence_template.md), [docs/162](./162_product_p10_tier1_evidence_pack.md), [docs/163](./163_product_forward_validation_post_refresh_smoke.md)

---

## Evidence manifest（git 外 evidence の追跡 · read-only）

P10 / 週次 preflight の git 外ファイルを `reports/YYYY-MM-DD/` に manifest 化（secret-free · commit 可）:

```bash
.venv/bin/python -m invis_alpha_os.cli.main log evidence-manifest \
  --task-id weekly_preflight_YYYYMMDD \
  --evidence-path outputs/evidence/p10_tier1_pre_YYYYMMDD.md \
  --command "docs/162 Step A" \
  --result ok \
  --summary "read-only preflight captured" \
  --report-date YYYY-MM-DD
```

- テンプレ: [docs/151](./151_product_p10_tier1_refresh_evidence_template.md)
- tier-1 pack: [docs/162](./162_product_p10_tier1_evidence_pack.md)
- `--strict` 時の taxonomy 一行: stderr（例 `taxonomy=EXPECTED_BLOCKED`）

---

<<< COPY FROM HERE >>>

## 週次 ops（read-only · まずここ）

```bash
cd /path/to/invest-alpha-os
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate ops-smoke --format json --strict
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate us-forward-returns --backtest-within-cache --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate peer-sync-forward-returns --format markdown
.venv/bin/python -m invis_alpha_os.cli.main validate jp-peer-sync-readiness --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main weekly-us-observation --dry-run --with-peer-sync --format markdown
```

**read-only 既定**: 上記 JSON 行は **`--strict` 必須**（週次デフォルト）。`repeat_signals` / `forward_stale_cache` 等の warn でも exit 2 となり **`all_ok=False` は正常**（蓄積中の repeat や stale cache 想定）。stderr に `taxonomy=EXPECTED_BLOCKED` 一行が出る。

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

- tier-1 cache refresh / live HTTP → [docs/162](./162_product_p10_tier1_evidence_pack.md) · [docs/151](./151_product_p10_tier1_refresh_evidence_template.md)
- refresh 後 forward smoke → [docs/163](./163_product_forward_validation_post_refresh_smoke.md)
- Gmail 配信 → 別 runbook
- `RULES.md` / portfolio 進捗 `[要確認]%` 更新

<<< COPY UNTIL HERE >>>
