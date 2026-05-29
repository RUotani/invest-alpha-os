# Provider execution approval request operating model

日付: 2026-05-30
ステータス: approved-by-task
関連: v39 Provider Approval Package, v41 Provider Safe Execution Harness, v43 Provider Approved Execution Runbook, `RULES.md` §1/§4

## 結論

- v44 approval request は future execution の最終 human-review packet であり、実 execution ではない。
- v39/v41/v43 の evidence を束ね、scenario、scope、approval phrase、not approved actions、planned commands、rollback、verification、stop conditions を一枚にする。
- live HTTP / cache write / actual refresh/import / manual import は別タスクの明示承認がある場合のみ実行候補になる。

## 生成方法

| 入力 | v44 での使い方 |
|---|---|
| v39 approval package | approval phrase and gate evidence |
| v41 safe execution harness | dry-run transcript and audit evidence |
| v43 operator runbook | operator checklist and planned command evidence |

## Human approval

- Human は selected scenario に対して exactly one primary approval phrase を返す。
- approval phrase がない場合、Cursor/local execution task へ進まない。
- scope を変更する場合は、ticker/date range/provider/scenario を明示して request を再生成する。

## Cursor execution boundary

- v44 の Cursor handoff は draft であり、`DRAFT ONLY - DO NOT RUN UNTIL HUMAN APPROVAL PHRASE IS PROVIDED` を含める。
- Cursor/local は別承認タスクでのみ future commands を扱う。
- Codex は source-only approval request 生成に限定し、live/cache/import/manual import を実行しない。

## Separation rationale

- Approval request と execution を同じ PR/タスクに混ぜると、承認範囲の誤読、secret/raw data exposure、cache rollback 不備が起きやすい。
- Source-only planning layer は reviewable で、CI/test 対象にでき、実行リスクを持ち込まない。

## 反証

- Approval request が増えることで ops layer が厚くなるリスクがある。
- 対策として v44 を final pre-approval layer とし、次は実行するなら別承認、実行しないなら投資ロジック側へ戻る。

## 次アクション

- 実 execution が必要なら、v44 request を添えて別の明示承認タスクを作る。
- 承認がない限り、live/cache/import/manual import は実行しない。
