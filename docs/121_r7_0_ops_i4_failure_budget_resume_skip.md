# R7.0-Ops-I4 — failure budget, resume/skip

**日付**: 2026-05-21 · **性質**: productive 8h の失敗上限拡大と重複 PR 回避

---

## 1. Why I4 after I3

- I3: 非critical 失敗を記録して継続（当時 max=3）
- 実運用: 3 件で `max_task_failures reached` となり 8h 枠がまだ短い
- 再実行: merge/close 済み task を再実行し重複 PR が発生

---

## 2. Policy

| 設定 | productive 値 |
|---|---|
| `--max-task-failures` | **8** |
| `--max-same-failure-category` | **4** |
| `--skip-existing-task-artifacts` | **on** |

カテゴリ: `pytest_failed`, `prepare_failed`, `pr_create_failed`, `ci_failed`, `unknown_task_failure`

---

## 3. Skip（失敗にカウントしない）

- open PR / remote branch / 同一 PR title / 当 run 内で完了済み
- 出力: `productive-longrun task skipped: task_id=... reason=...`
- evidence: `skipped_tasks`, `resume_policy`

read-only `gh pr list` が 502/504 のとき: 1 回リトライ → 警告を記録し git のみで判定（曖昧時は duplicate 回避のため skip 寄り）

---

## 4. Operator interpretation

| stop_reason | Action |
|---|---|
| `max_task_failures reached: 8` | failed_tasks 確認後に main 整理して再実行 |
| `max_same_failure_category reached: pytest_failed=4` | 同種障害（pytest/env）を修正してから再実行 |
| `SUCCEEDED_WITH_RECORDED_FAILURES` | 有用 PR を merge、重複は close |
| skip のみ多い | 既に処理済み — 新規 task を queue に足すか branch 命名を確認 |

---

## 5. Command

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_productive_true_longrun_8h.sh
```
