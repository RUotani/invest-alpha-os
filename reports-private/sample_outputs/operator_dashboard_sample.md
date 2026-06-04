> このサンプルは source-only / fixture-only の出力例です。
> 実データの正確性・鮮度を保証せず、売買指示ではありません。
> actual import / cache write / broker API / raw Excel parsing は実行していません。

# Operator Dashboard Sample（fixture-only）

> 観測・レビュー用ダッシュボード要約。売買指示ではありません。発注・実メール送信は行っていません。  
> 基準: main `f08b79d50decc3d81eccade76f8cebb1a434820a` / 生成: 2026-06-04

## 3行サマリー

- **週次**: 候補0件を抑制シグナルとして扱う copy-ready brief（fixture）
- **月次**: 現金回復優先の decision sheet（fixture 数値）
- **品質**: v109 portfolio review + v110 quarantine + v111 cross-review — **Import Readiness: NO-GO** / **Cache Write Readiness: NO-GO**
- **Hard Gates**: すべて遵守（live HTTP / cache write / broker / raw Excel なし）

## 進捗スナップショット（固定分母）

| Domain | 進捗 |
| --- | ---: |
| Safety / Hard Gates | 100% |
| Report MVP | 70% |
| Weekly / Monthly Ops | 73% |
| Portfolio Data Quality | 80% |
| Raw Input Quarantine | 87% |
| Actual Import Readiness | 0% |
| UX / Sample Outputs | 85% |

詳細: `docs/progress_dashboard.md`

## 週次（Weekly Candidate Brief）

- レポート日: 2026-06-04（fixture）
- 強い新規リスク候補: **0件**
- 現金: **11.7%**（minimum 15% 未満）
- 個別株: **19.6%**（target band 超過）
- Sanitized Input: **WARN**（v99 経路・共有要約）
- Gmail: **preview のみ**（`gmail_send_attempted=false` 設計）

→ 全文: `weekly_candidate_brief_sample.md`

## 月次（Monthly Decision Sheet）

- 現金: under minimum → **15〜20%回復を優先**
- 株式系: overweight → 新規リスク追加を抑制
- 個別株: 整理候補確認を優先

→ 全文: `monthly_decision_sheet_sample.md`

## ポートフォリオ品質（v109）

- 総合 severity: **WARN**（fixture）
- 現金比率・個別株比率の guardrail 警告
- manual confirmation 項目あり
- import readiness: **NO-GO**

→ 全文: `portfolio_data_quality_review_sample.md`

## Raw Input Quarantine（v110）

- safe fixture: **accepted_fixture**
- import_allowed: **false**
- cache_write_allowed: **false**
- raw Excel / broker: **blocked_by_hard_gate**

→ 全文: `raw_input_quarantine_review_sample.md`

## Cross Review（v111）

- cross_review_state: **manual_review_required**（safe fixture 時）
- v109 + v110 taxonomy keys 接続
- import / cache: **NO-GO**

→ 全文: `portfolio_quarantine_cross_review_sample.md`

## 次に人間が見るべきポイント

1. **2026-06-06 07:30 JST 以降** — natural scheduled weekly run（v104 status.json + artifact）
2. sample outputs の文言が週次/月次実出力と矛盾しないか
3. actual import 承認パッケージ（v110/v111 完了後も自動承認されない）

## Safety Footer

```text
NO-GO: live HTTP, cache write, actual import, broker API, raw Excel parsing, real email send, trading action
OK: fixture samples, source-only CLI, declaration-only quarantine, email preview generation
```
