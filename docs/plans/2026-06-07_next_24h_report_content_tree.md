# Next 24h Development Tree — Candidate Discovery OS + Report Content

Version: 2026-06-05（Post #487 merge）

## Project Scope（必須明記）

This project is **NOT** an auto-trading bot.  
No broker API.  
No order placement.  
No actual import / cache write without explicit approval.  
Goal is **global multi-asset candidate discovery and report generation** for human review.

## 現在地

- main: `da3bdc8`（#487 Weekly content improvement merged）
- Report MVP: **84%**（16/19）— readability contract + zero-candidate guard 完了
- scheduled natural run: **NOT_YET_OBSERVABLE** until 2026-06-06 07:30 JST

## Hard Gates（変更なし）

禁止:

- workflow_dispatch / workflow 直接変更
- live HTTP / market-data live fetch
- cache write / actual import / broker API
- raw Excel / raw broker export parsing
- env/secret 表示 / dependency 変更
- trading action / real email send

## Primary Queue — Candidate Discovery OS

| ID | 目的 | 出力 | 停止条件 |
| --- | --- | --- | --- |
| D1 | US/JP/ETF 横断候補の coverage 理由を統一 taxonomy へ | `signals/` reason codes + JA user layer | live data が必要 |
| D2 | score/veto pipeline の fixture vs real 分離を JSON schema に明記 | schema contract test | breaking change 要承認 |
| D3 | discovery merge 品質メトリクスを weekly copy に1行要約 | renderer + test | operator 増築化 |
| D4 | 候補あり週の結論テンプレ（0件以外）短縮 | weekly brief renderer | trading wording リスク |

## Secondary Queue — Report Content

| ID | 目的 | 出力 |
| --- | --- | --- |
| R1 | email preview が renderer 出力から正しく短縮抽出される回帰 | email parser tests |
| R2 | monthly + weekly 統合 index（fixture-only） | reports index page |
| R3 | scheduled 実 artifact vs sample 差分テンプレ | observation MD |

## Tertiary Queue — Observation

| 時刻 | 分類 | アクション |
| --- | --- | --- |
| Before 2026-06-06 07:30 JST | `NOT_YET_OBSERVABLE` | pending 更新のみ |
| After 07:30 + schedule success | `OBSERVABLE` | read-only `gh run list` / `gh run download` to `/tmp` |
| After 07:30 + no schedule | `OBSERVABILITY_MISS` | scheduler gap 分類レポート |

## 推奨 PR 順序

1. **#488**（本ロングラン）— MVP 85 readiness + scheduled observation pending 更新
2. **#489** — 本 development tree + MILESTONE/progress 整合
3. Post 07:30 JST — scheduled observation 結果 PR（success/fail/miss 分岐）
4. D1 — coverage reason taxonomy（signals 優先）
5. R1 — email/copy 整合回帰

## Decision Rules

- Natural scheduled run が未観測の間は manual dispatch で confidence を作らない。
- 候補0件 UX は #487 で完了。次は **候補あり週** と **discovery coverage** に注力。
- workflow JSON upload は proposal のまま。承認なしに workflow 触らない。
- Architecture Astronaut 検知: `operator/` 新機能は product ボトルネック解消時のみ。

## ChatGPT Handoff

1. 07:30 JST 経過後に `gh run list --workflow weekly_candidate_brief.yml` を read-only 実行。
2. `weekly_candidate_brief_sample.md` は #487 後の fixture 正本。実 run artifact と diff を取る。
3. 次の実装主戦場は `signals/` の discovery/coverage 品質と report renderer の候補あり週短縮。
