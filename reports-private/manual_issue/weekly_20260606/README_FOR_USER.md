# 2026-06-06 週次レポート — ユーザー向け要約（手動発行）

> **自動売買ではありません。** 候補発掘・監視・深掘り優先度のレポートです。  
> 生成: 2026-06-06 ローカル CLI（cache-only）· Gmail **未送信**

## 今週の結論

**今週は候補あり。** ただし現金比率・個別株比率の guardrail を優先し、**即時買いではなく深掘り順**に扱う。

- guardrail: 現金 **11.7%**（最低15%未満）/ 個別株 **19.6%**（目安10〜15%超過）
- 株式系合計 **67.8%** — 新規リスク追加より監視・整理・現金回復を優先

## Candidate count

| 区分 | 件数 |
| --- | ---: |
| 深掘り可能候補（パイプライン） | 18 |
| 新規リスク候補（行動分類） | 5 |
| 監視候補 | 11 |
| 追いかけない候補（過熱等） | 2 |
| 入力候補（パイプライン） | 58 |
| veto 該当 | 2 |

## Top picks / watch / veto / hold-off

| 役割 | 銘柄 | 要点 |
| --- | --- | --- |
| **第1候補** | 285A（キオクシア） | メモリ/NANDテーマ・モメンタム強いが **短期過熱**（20日 +73%） |
| **深掘り** | AAPL（Apple） | 52週高値近辺での反応 |
| **深掘り** | QQQ（Nasdaq 100 ETF） | 指数モメンタムの観測（リスクオン proxy） |
| **監視** | 285A | 急騰後の反転・需給確認待ち |
| **見送り** | 285A | overheat_caution — 追いかけ抑制 |

上位5件（深掘り候補表）: 285A, AAPL, QQQ, 6857（アドバンテスト）, 6273（SMC）

**Veto ログ（抜粋）:** 285A・5801 に `overheat_caution` / `overheated_caution`

## Portfolio guardrail

| 指標 | 値 | 判断 |
| --- | ---: | --- |
| 現金比率 | 11.7% | 最低15% **未満** → 現金回復優先 |
| 個別株比率 | 19.6% | 目安15% **超過** → 新規追加抑制 |
| 株式系合計 | 67.8% | 目標49%に対し overweight |
| Monthly Input | WARN | 対象月 2026-05 |

## 今日の action / do not action

### 今週やること

1. 第1候補（285A）の決算・バリュエーション・需給を確認
2. ポートフォリオ制約に照らして買える余力を確認
3. veto 条件を満たす候補は深掘り対象から外す
4. 現金11.7% → 最低15%方向の整理・監視を記録

### 今週やらないこと

- 根拠不足の新規個別株・高ベータ枠を追加しない
- 過熱候補（285A 等）を追いかけ判断にしない
- actual import / broker 連携 / cache write は **NO-GO**

## 自動売買ではないこと

本レポートは **Global Multi-Asset Candidate Discovery OS** の観測出力です。

- 注文実行・ブローカー API・自動売買は対象外
- Score/Veto 表は「深掘り優先度と安全確認」であり実行指示ではない
- `これは売買指示ではありません`（copy 本文にも明記）

## Gmail 未着の理由

| 要因 | 説明 |
| --- | --- |
| GitHub scheduled run | 2026-06-06 07:58 JST 時点で `event=schedule` **0件**（未発火） |
| real email send | 設計上 **NO-GO**（preview のみ） |
| 本発行 | ローカル CLI で **同内容を手動生成**（本ディレクトリ） |

メール相当のプレビュー（ローカル生成済み・git 対象外）: `email/email_preview.txt` / `email_preview.html`

## 明日（2026-06-07）の初日運用手順

1. `docs/v1_0_operator_start_here.md` を開く
2. `v1-readiness-check --format markdown` → `v1_usable_tomorrow: true` を確認
3. 本 README と `weekly_candidate_brief_copy.md` で週次判断
4. 週次ルーティンは `docs/v1_0_weekly_10min_flow.md`（10分）

```bash
cd /Users/uotani/Projects/invest-alpha-os
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown
env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-report-user-summary --format markdown --source composed
```

## Scheduled run 未発火（別記録）

- 分類: `OBSERVATION_PENDING_SCHEDULED_RUN_NOT_VISIBLE`
- workflow_dispatch は **未使用**（Hard Gate）
- 詳細: `reports-private/scheduled_observation/scheduled_run_observation_20260606.md`

## 読むべきファイル（優先順）

| 優先 | ファイル | 用途 |
| ---: | --- | --- |
| 1 | **本ファイル** | 今週の要約 |
| 2 | `weekly_candidate_brief_copy.md` | 全文（copy-ready） |
| 3 | `email/email_preview.txt` | メール相当の短縮版 |
| 4 | `weekly_report_user_summary.md` | ChatGPT 貼付用1ページ |
| 5 | `weekly_candidate_brief_v0_1.md` | フル markdown |

生成ログ: `generation_manifest.md`
