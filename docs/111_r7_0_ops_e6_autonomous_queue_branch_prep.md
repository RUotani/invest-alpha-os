# R7.0-Ops-E6 — autonomous queue branch preparation

**日付**: 2026-05-20 · **main 起点**: `c78f8ca` · **性質**: overnight 通常 queue の branch prepare / push

---

## 1. Context

- Ops-E5: dev-loop PR-create smoke は一意 branch で成功（PR #60）
- `overnight_safe_3h` trial: `preflight: branch not pushed to origin: work/r7-0-ops-e-docs-status-microfix` で安全停止（evidence 記録済み）

---

## 2. Fix

| 項目 | 動作 |
|---|---|
| branch template | `work/dev-loop/autonomous/{task_id}/{run_id}` — sanitize 展開 |
| `docs_status_microfix` | `prepare_for_pr` + `docs/01_development_status.md` marker |
| 他 task | template のみ（手動 branch 準備まで PR 前停止） |
| push 前 | `git ls-remote` read-only、force push / branch 削除禁止 |
| evidence | `preparation_preflight` に task_id / branch / remote / ahead / changed_files |

---

## 3. Safety

- auto-merge 禁止
- PR ゲート維持（`CONFIRM_OPERATOR_DEV_LOOP` + `CONFIRM_GITHUB_PR_CREATE`）
- live HTTP / cache write / Gmail send なし

---

## 4. Real guarded overnight mini trial（merge 後・人間）

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES

operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue.yaml \
  --profile overnight_safe_3h \
  --execute-dev-loop \
  --create-pr \
  --max-tasks 1 \
  --max-prs 1
```

**期待**: 第一 task（docs microfix）が prepare → push → PR まで進む。merge は人間判断。
