# Cursor Final Report — Emergency Weekly Manual Issue 2026-06-06

## 結論

2026-06-06 分の weekly report を **ローカル CLI で生成済み**。ユーザーは `README_FOR_USER.md` から読める。Hard Gate violation: **none**。

## Main State

- base main: `fce211a15a5ea06ff1e196152278ed4cb505cff3`
- v1_usable_tomorrow: **true**

## 生成結果

| 項目 | 結果 |
| --- | --- |
| candidate 週 | **あり**（深掘り可能18 / 新規リスク候補5） |
| 第1候補 | 285A（キオクシア）— 過熱 caution あり |
| guardrail | 現金11.7% / 個別株19.6% |
| email preview | 生成済み（送信なし） |

## ユーザー入口

`reports-private/manual_issue/weekly_20260606/README_FOR_USER.md`

## Gmail 未着

scheduled run 未発火 + real email NO-GO。手動 CLI 発行で代替。

## Safety

未実行: workflow_dispatch, workflow 変更, real email, live HTTP, cache write, import, broker

## Next

2026-06-07 初日運用: `docs/v1_0_operator_start_here.md`
