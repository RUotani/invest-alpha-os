# R7.0-Ops-I7B — v2 queue scope fix

**日付**: 2026-05-22 · **性質**: `docs/smoke.md` scope violation で v2 run が 0 task 停止

---

## 1. What happened

- v2 12h run `20260522T130932Z`: `tasks=0/32`, `stop_reason=scope violation ... docs/smoke.md`
- Validator は正しく停止（`docs/smoke.md` は quarantine 用の試行残骸）
- 第一 task の `change_file` が tests のみで、作業ツリーに `docs/smoke.md` が残っていると scope に引っかかる

---

## 2. Fix

1. `ops_i7_v2_post_run_review_tests` の `change_file` → `docs/125_ops_i7_v2_post_run_review_tests.md`（`docs/` を allowed_paths に含む）
2. `productive_queue_scratch_violations()` — queue 定義で `docs/smoke.md` 等を拒否
3. `_has_forbidden_dirty_paths` — dirty な `docs/smoke.md` を quarantine として拒否

---

## 3. Next action

1. Merge I7B PR
2. Confirm `docs/smoke.md` 不在（または quarantine 済み）
3. Rerun v2 12h with `autonomous_dev_queue_productive_12h_v2.yaml`
