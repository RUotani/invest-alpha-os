# R7.0-Ops-I7E — Eliminate runtime fixture marker dirty path

**日付**: 2026-05-22 · **性質**: task 2 で `docs/ops_dev_loop_test_marker.md` scope violation

---

## 1. What happened

- I7D 後 v2 run: task 1 skip（existing PR #136）、task 2 で停止
- `stop_reason=scope violation ... docs/ops_dev_loop_test_marker.md`
- preflight 時点は clean — **unit test の `execute=True` prepare が ROOT_DIR に marker を書いていた**（preflight pytest 91 passed 時に生成）

---

## 2. Fix

1. `PRODUCTIVE_QUARANTINE_PATHS` に `docs/ops_dev_loop_test_marker.md` を追加
2. `docs/*test_marker*.md` を productive change_file として拒否
3. productive runtime: `allowed_paths` 外の dirty を `_productive_unallowed_dirty_paths` で拒否
4. テスト fixture は `_isolated_repo(tmp_path)` のみ使用 + autouse cleanup

---

## 3. Next action

1. Merge I7E PR
2. ローカル marker 残骸を削除し clean tree を確認
3. v2 12h を再開（task 2 から）
