> このサンプルは source-only / fixture-only の出力例です。
> 実データの正確性・鮮度を保証せず、売買指示ではありません。
> actual import / cache write / broker API / raw Excel parsing は実行していません。

# ChatGPT One-Page Operator Summary — Sample

## 今週の結論

- 強い新規リスク候補 **0件**（抑制シグナルとして扱う）
- 現金 **11.7%**（minimum 15% 未満）→ 監視・整理・現金回復を優先
- 個別株 **19.6%**（target band 超過）→ 新規追加より整理候補確認
- Sanitized Input: **WARN**（v99 共有要約経路）

## Portfolio Guardrails

| 指標 | 値 | 判断 |
| --- | ---: | --- |
| 現金比率 | 11.7% | minimum 15% 未満 |
| 個別株比率 | 19.6% | target max 15% 超過 |
| 株式系合計 | 67.8% | 目標49%に対し overweight |
| 候補総数 | 0 | データ品質・キャッシュ制約で候補なし |

## Data Quality / Quarantine

- Portfolio Data Quality: **WARN**（v109 fixture）
- Raw Input Quarantine: **accepted_fixture**（v110）
- Cross-Review: **manual_review_required**（v111）
- Import Readiness: **NO-GO**
- Cache Write Readiness: **NO-GO**

## Suggested Human Review

1. 対象月 **2026-05** が最新 portfolio input か確認
2. `currency=JPY` / `amount_unit=man_yen` が共有契約と一致するか確認
3. 現金・個別株 guardrail が最新入力でも継続しているか確認
4. 週次メールは **preview のみ**（`gmail_send_attempted=false`）

## NO-GO Boundaries

- live HTTP / market-data fetch: **未実行**
- cache write / actual import: **未実行**
- broker API / raw Excel parsing: **未実行**
- trading action / real email send: **未実行**

## Next Actions

1. `v1-readiness-check --format markdown` で v1.0 core 12/12 を確認
2. `weekly-report-user-summary --source composed` で one-page を取得
3. `docs/v1_0_weekly_10min_flow.md` で週次10分レビュー
4. 2026-06-06 07:30 JST 以降の scheduled run を read-only 観測
