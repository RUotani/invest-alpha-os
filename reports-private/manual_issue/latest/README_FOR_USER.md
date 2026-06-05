# 今日読むファイル — v1.0 週次レポート（latest）

> **この1ファイルが初日運用の固定入口です。**  
> 自動売買ではありません。深掘り候補の観測レポートです。

| 項目 | 値 |
| --- | --- |
| レポート日 | **2026-06-06** |
| 実体パック | [weekly_20260606/](../weekly_20260606/) |
| 全文 copy | [weekly_20260606/weekly_candidate_brief_copy.md](../weekly_20260606/weekly_candidate_brief_copy.md) |

---

## 今週の結論（1分）

**候補あり週。** guardrail（現金11.7%・個別株19.6%）を優先し、**即時買いではなく深掘り順**。

## 深掘り候補（売買指示ではない）

以下は **調査・確認用の深掘り候補** です。注文・売買の推奨ではありません。

| 銘柄 | 扱い | 確認すること |
| --- | --- | --- |
| **285A**（キオクシア） | 第1深掘り候補 | NAND/DRAM需給・決算・**過熱**（20日+73%）後の反転リスク |
| **AAPL**（Apple） | 深掘り候補 | 52週高値近辺・サービス/為替・バリュエーション |
| **QQQ**（Nasdaq 100 ETF） | 深掘り候補 | 指数モメンタム・breadth・リスクオン姿勢の変化 |

- 285A は **監視** と **見送り（overheat_caution）** も併記 — 追いかけ判断は抑制
- 深掘り前に: 反証・veto・portfolio 制約を必ず確認

## Portfolio guardrail

- 現金 **11.7%** < 最低15% → 現金回復・新規リスク抑制
- 個別株 **19.6%** > 目安15% → 新規個別株追加を急がない

## 今週やること / やらないこと

**やる:** 上記3銘柄の根拠・反証・需給を **調査メモ** として確認  
**やらない:** 根拠不足の追加・過熱追いかけ・actual import / broker / cache write

## 別ブロッカー（初日運用は止めない）

| ブロッカー | 状態 | 初日運用への影響 |
| --- | --- | --- |
| GitHub scheduled run | `OBSERVATION_PENDING_SCHEDULED_RUN_NOT_VISIBLE` | **なし** — 本 manual pack で代替済み |
| Gmail 配信 | v1.1 承認済み — secrets 設定後は `weekly-report-email-send --send` | 未設定時は本 README + copy で閲覧可 |
| CI JSON artifact | workflow 承認待ち | **なし** — ローカル JSON は生成済み（週次dir） |

初日運用（2026-06-07）は **v1_usable_tomorrow: true** のまま継続。

## 詳細を読むとき

1. [weekly_20260606/README_FOR_USER.md](../weekly_20260606/README_FOR_USER.md) — 週次フル要約
2. [weekly_20260606/weekly_candidate_brief_copy.md](../weekly_20260606/weekly_candidate_brief_copy.md) — 全文
3. [docs/v1_0_operator_start_here.md](../../../docs/v1_0_operator_start_here.md) — 運用索引

## Gmail 自動送信（v1.1）

セットアップ: `docs/v1_1_gmail_auto_send_setup.md`  
secrets 設定後、週次 workflow または CLI で SMTP 送信。失敗時も本 README が fallback。

## 安全メモ

これは売買指示ではありません。Global Multi-Asset Candidate Discovery OS の観測出力です。
