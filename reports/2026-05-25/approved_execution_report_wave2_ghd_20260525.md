# Approved execution report — wave2 G/H/D（2026-05-25）

## 3行サマリー
- **H**: shadow 2 positions · resolved_links=**2**（MSFT/AAPL ↔ observation_log id）。
- **G**: `portfolio_observation_acceptance.yaml` → **40%** · tier **P0+P1**。
- **D**: Gmail **sent_ok**（`outputs/operator/daily_usage/2026-05-25/`）。

前提: E/F 実行済み（log 94行 · forward matched=3 thin）。

---

## 承認 H — shadow linkage

| 項目 | 結果 |
| --- | --- |
| path | `outputs/shadow_portfolio/positions.jsonl` |
| positions | 2（MSFT, AAPL） |
| resolved_links | 2 |

---

## 承認 G — portfolio %

| 項目 | 値 |
| --- | --- |
| human_accepted_percent | **40** |
| accepted_tier | **P0+P1** |
| config | `config/portfolio_observation_acceptance.yaml` |

---

## 承認 D — Gmail

| 項目 | 結果 |
| --- | --- |
| dry-run | dry_run_ok |
| send | **sent_ok** · `email_sent.json` 作成 |
| bundle | `outputs/operator/daily_usage/2026-05-25/` |

（宛先・トークンはログ・チャットに出力していない）

---

## Read-only 確認

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format markdown
```

---

## 残タスク

- [ ] forward P3 **usable**（thin → usable · 週次蓄積）
- [ ] 次回 weekly / P10 は**新規承認**
