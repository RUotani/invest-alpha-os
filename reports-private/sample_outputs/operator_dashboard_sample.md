> このサンプルは source-only / fixture-only の出力例です。
> 実データの正確性・鮮度を保証せず、売買指示ではありません。
> actual import / cache write / broker API / raw Excel parsing は実行していません。

# Operator Dashboard Sample（fixture-only）

**総合ステータス:** 観測・レビュー準備完了 / **Import Readiness: NO-GO** / **Cache Write Readiness: NO-GO**  
基準: main `cd32558`（#471 merged） / 生成: 2026-06-04

## 今週見るべき3行

1. 候補 **0件** と現金 **11.7%** → 新規リスク追加より監視・現金回復を優先
2. 個別株 **19.6%**（target 超過）→ 整理候補の確認を優先
3. **2026-06-06 07:30 JST** 以降の natural scheduled run を read-only 観測（Epoch 4）

---

## ステータスカード

| カード | 状態 | 要点 |
| --- | --- | --- |
| **Report MVP** | 70% | weekly/monthly sample 完成、scheduled 観測待ち |
| **Data Quality** | WARN | v109 fixture — 現金・個別株 guardrail |
| **Quarantine** | accepted_fixture | v110 safe fixture、import/cache **NO-GO** |
| **NO-GO** | 遵守 | live HTTP / cache / broker / raw Excel / 実メール なし |
| **Next Human Review** | 4項目 | 対象月・単位契約・guardrail・scheduled artifact |

---

## Portfolio Guardrails（fixture）

| 指標 | 値 | ラベル |
| --- | ---: | --- |
| 現金比率 | 11.7% | minimum 15% **未満** |
| 個別株比率 | 19.6% | target max 15% **超過** |
| 株式系合計 | 67.8% | 目標49%に対し overweight |
| 強い新規リスク候補 | 0件 | 抑制シグナル |

---

## 進捗スナップショット（固定分母）

| Domain | 進捗 |
| --- | ---: |
| Safety / Hard Gates | 100% |
| Report MVP | 70% |
| Weekly / Monthly Ops | 73% |
| Portfolio Data Quality | 87% |
| Raw Input Quarantine | 87% |
| Actual Import Readiness | 0% |
| UX / Sample Outputs | 90% |

詳細: `docs/progress_dashboard.md` / 1ページ要約: `chatgpt_one_page_summary_sample.md`

---

## レポートリンク

| 種別 | ファイル | ハイライト |
| --- | --- | --- |
| 週次 | `weekly_candidate_brief_sample.md` | 候補0 / 現金不足 / preview email only |
| 月次 | `monthly_decision_sheet_sample.md` | 現金回復最優先 |
| 品質 | `portfolio_data_quality_review_sample.md` | WARN / **Safety Summary** |
| Quarantine | `raw_input_quarantine_review_sample.md` | accepted_fixture |
| Cross | `portfolio_quarantine_cross_review_sample.md` | manual_review_required |

---

## Safety Summary

- 売買指示ではありません（source-only / fixture-only）
- `gmail_send_attempted=false` 設計（preview のみ）
- CLI: `portfolio-data-quality-review` / `sample-output-pack`（stdout のみ、cache write ではない）

```text
NO-GO: live HTTP, cache write, actual import, broker API, raw Excel parsing, real email send, trading action
OK: fixture samples, declaration-only quarantine, email preview generation
```
