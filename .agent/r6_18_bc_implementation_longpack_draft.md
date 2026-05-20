# DRAFT — R6.18 B1 opt-in signals US cache preview (do not execute)

```text
DO NOT EXECUTE UNTIL R6.18-B+C PLANNING PR IS MERGED AND USER APPROVES IMPLEMENTATION.
```

## 実行場所

Cursor右側Agent（右ペイン）。ターミナル用ではない。

## 目的

- **B1 only**: `signals --us-cache-preview` を追加
- 既存 `us_cache_preview_opt_in` builder を再利用
- **daily / signals default 不変**
- observation-only · cache-only · no scoring

## 現在状態（実装開始時に更新）

- `origin/main`: （planning PR merge 後の SHA）
- inventory: fresh_enough 16 / stale 0（R6.17-D 前提）
- design: [docs/74](../docs/74_r6_18_bc_cache_only_connection_design.md)
- checklist: [docs/75](../docs/75_r6_18_bc_default_enablement_readiness_checklist.md)
- review pack: [docs/76](../docs/76_r6_18_bc_implementation_review_pack.md)
- Codex planning verdict: （実装前に記入）

## 許可 scope

- `signals` CLI に `--us-cache-preview`（default **False**）
- preview 節の append（既存 builder 再利用）
- tests + docs（実装範囲内）
- PR 作成 · CI 確認

## 禁止（`.agent/standard_clauses.md` に加えて）

- live HTTP · cache write
- workflow / Makefile / `pyproject.toml`（明示承認なし）
- daily / signals **default** 変更
- default enablement
- scoring · ranking 変更 · aggregate score
- portfolio / macro / Veto 接続
- 売買推奨・buy/sell 語彙
- cache JSON commit · `.env` commit / 出力
- main direct push · force push · branch/worktree 削除
- R6.18 以外フェーズ混在

## Sound policy

`.agent/standard_clauses.md` — **completion sound only** at end.

## Stages

1. Preflight: `origin/main` FF · clean tree
2. Branch: `work/r6-18-b1-signals-us-cache-preview`（または一意 suffix）
3. Implement B1（CLI + signals output path + reuse builder）
4. Tests（下記）
5. Docs microfix（docs/01 · runbook 軽量）
6. PR · CI
7. Merge **only if authorized**（squash · `--delete-branch=false`）

## Future tests (required)

- signals default excludes preview
- signals opt-in includes preview
- daily default unchanged（回帰）
- daily opt-in unchanged（回帰）
- forbidden terms absent from preview section
- no live HTTP guard
- no cache write guard
- stale / freshness_unknown — returns not used（note）
- output contract columns（symbol · latest_date · freshness_status · close · return_* · volume_status · note）

## Output contract

[docs/74 §5](../docs/74_r6_18_bc_cache_only_connection_design.md) に準拠。

## Architecture quality gate

実装 PR 前に必要なら **Claude Code**（`.agent/claude_arch_review_template.md`）:

- default パス不変
- signals momentum / Veto と preview 分離
- rollback = flag off

## Final report template

```markdown
# R6.18 B1 Signals US Cache Preview Final Report

## State Capsule
- starting main:
- final main:
- branch:
- PR:
- merge:
- CI:
- next decision:

## result
| item | result |
|---|---|
| B1 signals opt-in | pass/fail |
| daily default unchanged | pass/fail |
| signals default unchanged | pass/fail |
| forbidden terms | pass/fail |
| live HTTP / cache write | no |
| default enablement | no |

## safety
| item | result |
|---|---|
| product scope | B1 only |
| ... | ... |

## failures
- none / ...

## decisions needed
1. ...

## next actions
1. ...
```

## Final report format

`.agent/report_template.md` — merge 欄は **not performed unless authorized**。
