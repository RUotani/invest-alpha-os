# Provider Safe Execution Harness operating model

日付: 2026-05-29
ステータス: approved-by-task
関連: v36 OHLCV Provider Automation Core, v39 Provider Approval Package & Execution Planner, `RULES.md` §1/§4/§12

## 結論

- Provider execution は approval package だけでは実行しない。
- v41 harness は **source-only / dry-run transcript-only** の preflight layer とする。
- live HTTP / cache write / actual refresh/import / manual import は、別タスクで明示 approval phrase がある場合のみ検討する。

## 採用した運用モデル

| 層 | 役割 | 実行可否 |
|---|---|---|
| v36 provider registry | provider candidates and policy | 実行なし |
| v39 approval package | required gates and approval phrases | 実行なし |
| v41 safe execution harness | transcript, preflight, rollback, verification | 実行なし |
| future Cursor/local task | approved live/cache/import execution | 別承認が必要 |

## Hard Gates

以下は v41 harness では常に non-executing とする。

- `LIVE_HTTP`
- `PUBLIC_OHLCV_SOURCE_LIVE_FETCH`
- `JQUANTS_GATED_REFRESH`
- `CACHE_WRITE`
- `ACTUAL_REFRESH`
- `ACTUAL_IMPORT`
- `MANUAL_ACTUAL_IMPORT`
- `BROKER_OR_MANUAL_RAW_DATA_HANDLING`
- `ENV_OR_SECRET_REQUIRED`
- `WORKFLOW_DEPENDENCY_OR_PYPROJECT_CHANGE`
- `TRADING_ACTION`

## Handoff

- ChatGPT: approval package / harness transcript をレビューして、必要な approval phrase と scope を整理する。
- Codex: source-only model, tests, CLI/report integration を維持する。
- Cursor/local: 明示承認がある場合のみ、別タスクで live/cache/import を実行する。

## Rollback / Verification

- v41 自体は状態変更しないため rollback は不要。
- 将来 cache write/import を行う場合は、事前 cache inventory、対象 ticker/date range、postcheck をセットで残す。
- raw provider response、secret/env values、broker/manual raw file contents は出力しない。

## 反証

- Harness が execution に近い名前を持つため、誤って実行可能 CLI に見えるリスクがある。
- 対策として CLI options は `--report-date` / `--out-dir` / `--format` のみに限定し、`--live` / `--write-cache` / `--execute` / `--import` を追加しない。

## 次アクション

- v41 harness report を Cursor 側で dry-run 生成する。
- 実 execution が必要な場合は、approval package と harness transcript を根拠に別の明示承認タスクを作る。
