# R7.0-Ops-E5 — unique branch for dev-loop PR-create smoke

**日付**: 2026-05-20 · **main 起点**: `6cbdb9c` · **性質**: smoke branch 一意化と push 前 preflight 強化

---

## 1. Problem (Ops-E4 real smoke)

- guarded smoke が `prepare_failed` で停止
- 原因: 固定 branch `work/r7-0-ops-e4-dev-loop-pr-create-smoke` の再利用により `git push` が non-fast-forward で拒否
- evidence は `outputs/operator/dev_loop/<run_id>/` に記録済み

---

## 2. Fix

| 項目 | 動作 |
|---|---|
| branch template | `work/dev-loop-smoke/{run_id}` — `run_id` を sanitize して展開 |
| push 前 | `git ls-remote --heads origin <branch>` で remote 存在を read-only 確認 |
| remote 既存 | force push せず `remote_branch_exists` で controlled stop |
| push 失敗 | non-fast-forward 等は `push_rejected_non_ff`、detail は sanitize |
| evidence | `preparation_preflight` に current/intended branch、base、ahead count、remote exists |

---

## 3. Safety

- force push 禁止
- branch 削除禁止
- auto-merge 禁止
- PR 作成 gate は従来通り（`CONFIRM_OPERATOR_DEV_LOOP` + `CONFIRM_GITHUB_PR_CREATE`）

---

## 4. Real guarded smoke（merge 後・人間実行）

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES

operator-runner dev-loop \
  --task-queue config/tasks/dev_loop_pr_create_smoke_queue.yaml \
  --profile smoke_20min \
  --execute-dev-loop \
  --create-pr \
  --max-tasks 1 \
  --max-prs 1
```

**期待**: `completed`、一意 branch への push、PR URL が evidence に記録。merge は人間判断。

**朝確認**: open PR、CI green、evidence の `intended_branch` が run ごとに異なること。
