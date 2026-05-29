# Provider approved execution runbook operating model

日付: 2026-05-29
ステータス: approved-by-task
関連: v39 Provider Approval Package, v41 Provider Safe Execution Harness, `RULES.md` §1/§4

## 結論

- v43 runbook は future approved execution の operator checklist であり、実 execution ではない。
- approval phrase、scope、future command plan、preflight、rollback、verification、stop conditions を source-only で固定する。
- live HTTP / cache write / actual refresh/import / manual import は別タスクの明示承認がある場合のみ検討する。

## 採用した境界

| 層 | 役割 | 実行可否 |
|---|---|---|
| v39 approval package | approval phrases and gates | 実行なし |
| v41 safe execution harness | dry-run transcript and preflight | 実行なし |
| v43 approved execution runbook | operator checklist and command plan | 実行なし |
| future Cursor/local task | approved execution | 別承認が必要 |

## Operator responsibilities

- 事前に scenario、provider、ticker、date range、approval phrase を一致確認する。
- command plan は `# NOT EXECUTED - requires explicit approval` として扱う。
- 実行前に cache/import 対象 path と ticker/date delta を明示する。
- secret、raw provider response、broker/manual raw data、reports-private write を出力しない。

## ChatGPT / Codex / Cursor boundaries

- ChatGPT: approval phrase と scope の妥当性をレビューする。
- Codex: source-only runbook、tests、CLI/report/context pack integration を維持する。
- Cursor/local: 別承認がある場合のみ future live/cache/import execution を行う。

## Supported scenarios

- `public_ohlcv`
- `jquants_refresh`
- `cache_write`
- `actual_import`
- `manual_import`

## 反証

- Runbook に future commands が載るため、実行指示と誤読されるリスクがある。
- 対策として各 command を `NOT EXECUTED` marker 付きにし、CLI は report generation だけに限定する。

## 次アクション

- Future execution が必要なら、v39/v41/v43 を根拠にした別の明示承認タスクを作る。
- 承認がない限り、Codex は live/cache/import/manual import を実行しない。
