# Project Goal — Global Multi-Asset Candidate Discovery OS

版: 2026-06-06（Post #494 Long-Run）

## English（scope boundary）

This project is **NOT** an auto-trading bot.

- No broker API.
- No order placement.
- No direct account connection.
- No actual import / cache write without explicit human approval.

**Primary goal:** global multi-asset candidate discovery, cross-asset comparison, risk guardrails, and report generation for human review.

## 日本語（ユーザー向け）

本プロジェクトは**自動売買ボットではない**。

- ブローカー API 接続なし
- 注文実行なし
- 口座への直接接続なし
- 実データ import / cache write は明示承認まで NO-GO

**目的:** グローバル複数資産を横断して、上昇可能性・急騰可能性・割安修正可能性のあるセグメントや銘柄候補を抽出し、根拠・反証・優先度をレポートすること。

## 成果物の定義

| 種別 | 説明 |
| --- | --- |
| Discovery | US / JP / ETF 等の横断候補抽出と coverage 理由の統一 |
| Scoring / Veto | score band・veto 条件・portfolio guardrail の可視化 |
| Reports | Weekly Candidate Brief / Monthly Decision Sheet / email preview |
| Observation | scheduled run・artifact schema・local verify（read-only） |

## 明示的に対象外

- 自動売買・発注・ポジション執行
- raw broker export / raw Excel の直接パース（承認前）
- live market data fetch（cache-only 原則）
- real email send（preview / dry-run のみ）

## 関連ドキュメント

- `docs/plans/2026-06-07_next_24h_candidate_discovery_tree.md`
- `docs/plans/2026-06-07_next_24h_candidate_discovery_longrun.md`
- `docs/progress_dashboard.md`（参考ドメイン Candidate Discovery OS）
