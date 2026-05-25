# Product — shadow portfolio seed (observation linkage · P1)

**Status**: manual setup · read-only evaluator  
**Related**: [docs/154](./154_product_portfolio_progress_proposal.md)

---

## 目的

portfolio rubric **P1（linkage）** を進めるため、`outputs/shadow_portfolio/positions.jsonl` に観測と紐づく shadow 行を置く。

## テンプレ（repo 同梱 · commit 可）

`config/examples/shadow_portfolio_positions.example.jsonl`

## 手順（人間 · outputs 書込）

1. 週次 `--write-observation-log` 実行後、`observation_log` から対象行の `id` を控える
2. 例ファイルをコピー:

```bash
mkdir -p outputs/shadow_portfolio
cp config/examples/shadow_portfolio_positions.example.jsonl outputs/shadow_portfolio/positions.jsonl
# edit thesis_evidence_ids to match observation_log row ids, e.g.:
#   "thesis_evidence_ids": ["<uuid-from-observation_log>"]
```

3. 検証（read-only）:

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
```

## 評価

- `portfolio.readiness` の P1 は `positions_with_resolved_links > 0` で pass
- `shadow_seed_hint` が出る場合は shadow ファイル未配置

## 禁止

- 自動 sizing / 売買推奨
- shadow ファイルの Agent 無承認 bulk 書込
