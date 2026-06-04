# Sample Output 再生成手順（fixture-only）

版: v0.1 / 2026-06-04

## 方針

- **cache write ではない** — stdout または手動で `reports-private/sample_outputs/` に反映
- raw path / broker export / actual import は使わない
- 週次・月次は既存 copy-ready fixture 由来の md を維持（必要時のみ手動編集）

## CLI（stdout）

```bash
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main portfolio-data-quality-review --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main raw-input-quarantine-review --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main portfolio-quarantine-cross-review --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main sample-output-pack --format markdown
```

`sample-output-pack` は品質 + quarantine + cross-review を1本に連結します（ファイル自動書き込みなし）。

## ファイル反映例

```bash
{
  printf '%s\n\n' '> このサンプルは source-only / fixture-only の出力例です。' '...'
  env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main portfolio-data-quality-review --format markdown 2>/dev/null
} > reports-private/sample_outputs/portfolio_data_quality_review_sample.md
```

先頭 disclaimer は `reports-private/sample_outputs/README.md` を参照。
