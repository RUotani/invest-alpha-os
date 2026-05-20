# R7.0-Ops-E3 — graceful PR-create failure handling

**日付**: 2026-05-20 · **main 起点**: `2ef1412` · **性質**: `gh pr create` 失敗時の controlled stop

---

## 1. Purpose

guarded `--execute-dev-loop --create-pr` smoke で `gh pr create` が exit 1 になった際、traceback で落ちず `stopped + evidence` で安全停止する。

---

## 2. Behavior

| 条件 | 動作 |
|---|---|
| `gh pr create` exit != 0 | `status=stopped`, `stop_reason=pr_create_failed` |
| preflight 失敗（branch 不在 / main 等） | `status=stopped`, `stop_reason=preflight: ...` |
| gate 不足 | 従来通り `blocked`、PR 作成なし |
| dev-loop + `--stop-on-failure` | task 失敗で後続 task を停止 |

---

## 3. Evidence

`outputs/operator/pr_loop/<run_id>/evidence_summary.json` に追加:

- `pr_create_exit_code`
- `pr_create_detail`（sanitized stderr/stdout、secrets 除外）

dev-loop evidence は task_results と stop_reason に反映。

---

## 4. Safety

- auto-merge 禁止維持
- `gh pr merge` / `gh pr close` 禁止維持
- real GitHub API 失敗も controlled stop（traceback なし）

---

## 5. Follow-up

- Ops-E4 で dev-loop 経由 PR-create smoke（詳細 **[docs/109](./109_r7_0_ops_e4_dev_loop_pr_create_smoke.md)**）
