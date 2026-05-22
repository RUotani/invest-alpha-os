# R7.0-Ops-I7D — Fix v2 fixture scope on second task

**日付**: 2026-05-22 · **性質**: 2 番目 task で `docs/dev_loop_marker_fixture.md` scope violation

---

## 1. What happened

- I7C 後 v2 run: `tasks=1/32`, `prs=1`（PR #136 作成成功）
- 2 番目 task `ops_i7_v2_classify_interruption_tests` で停止
- `stop_reason=scope violation ... docs/dev_loop_marker_fixture.md`
- v2 YAML の `change_file` は `tests/test_operator_dev_loop.py`（正しい）。停止原因は **作業ツリーに残った test fixture 残骸**

---

## 2. Fix

1. `PRODUCTIVE_QUARANTINE_PATHS` に `docs/dev_loop_marker_fixture.md` を追加
2. `_is_productive_fixture_change_file()` — productive queue の `docs/*fixture*.md` を拒否
3. dirty / 実行前 quarantine 検査を拡張

---

## 3. Next action

1. Merge #136（open なら）と I7D PR
2. `docs/dev_loop_marker_fixture.md` を repo 外へ退避
3. v2 12h を再開（task 2 から resume または新 run）
