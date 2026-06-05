# Next 24h Development Tree — Candidate Discovery OS

Version: 2026-06-06（Post #495 merge）

## Project Scope

This project is **NOT** an auto-trading bot. No broker API. No order placement. No direct account connection.

Primary goal: **global multi-asset candidate discovery**, cross-asset comparison, risk guardrails, and report generation.

## 現在地

- main: `af6543a`（#495 D4 candidate-positive conclusion merged）
- Report MVP: **17/20（85%）** — zero-candidate (#487) + candidate-positive (#495)
- Candidate Discovery OS: D1–D4 完了（#491–#495）
- scheduled natural run: **NOT_YET_OBSERVABLE** until 2026-06-06 07:30 JST

## Hard Gates（変更なし）

禁止: workflow_dispatch / workflow 直接変更 / live HTTP / cache write / actual import / broker API / raw Excel / env secret / dependency change / trading action / real email send

## Completed — Discovery Queue

| ID | 内容 | PR |
| --- | --- | --- |
| D1 | coverage reason taxonomy | #491 |
| D2 | JSON `score_veto_pipeline_source` / `coverage_reason_codes` | #492 |
| D3 | discovery merge 1行要約 | #493 |
| D4 | 候補あり週結論テンプレ短縮 | #495 |

## Primary Queue — Next Discovery

| ID | 目的 | 出力 | 停止条件 |
| --- | --- | --- | --- |
| D5 | Global asset radar skeleton（fixture-only） | `signals/` radar module + tests | live data 必須 |
| D6 | Theme/segment ranking contract | schema + JA user layer | operator 増築化 |
| D7 | Candidate queue schema（cross-market） | JSON contract tests | breaking change |
| D8 | Momentum/value/macro overlay 要約行 | weekly copy 1行 | trading wording |

## Secondary Queue — Report / Ops

| ID | 目的 | 出力 |
| --- | --- | --- |
| R1 | email compact extraction 回帰（候補あり週） | tests（#495 着手済み） |
| R2 | scheduled artifact vs sample 差分テンプレ | observation MD |
| R3 | workflow JSON upload 承認後 contract 再検証 | local verify harness |

## Tertiary — Observation

| 時刻 | 分類 | アクション |
| --- | --- | --- |
| Before 2026-06-06 07:30 JST | `NOT_YET_OBSERVABLE` | pending 更新のみ |
| After 07:30 + schedule success | `SCHEDULE_SUCCESS` | read-only `gh run download` → `/tmp` |
| After 07:30 + no schedule | `SCHEDULE_MISS` | gap 分類レポート |

## 推奨 PR 順序

1. Post 07:30 JST — scheduled observation PR（P1/P2）
2. D5 — global asset radar skeleton
3. workflow JSON upload（**承認後のみ** — proposal 参照）
