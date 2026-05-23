# R7.0-Ops-I5 — repair productive queue failing tasks

**日付**: 2026-05-21 · **性質**: I4 後の pytest_failed クラスター修復

---

## 1. I4 は設計どおり

Run `20260521T142301Z` は skip 成功後、同一カテゴリ `pytest_failed` が 4 連続で `max_same_failure_category reached: pytest_failed=4` により停止。runner 基盤ではなく **queue/task 定義** の問題。

---

## 2. Root causes（4 tasks）

| task_id | 原因 |
|---|---|
| `ops_i_min_max_runtime_tests` | `change_file` が `.py` なのに markdown マーカー → SyntaxError |
| `ops_i_profile_runtime_warning` | `-k profile_runtime` が 0 件 → pytest exit 5 |
| `ops_i_true_longrun_profile_validation` | 自己参照クラスター・前 task 汚染リスク |
| `ops_i_heartbeat_coverage` | 同上（I3/I4 で既カバー） |

---

## 3. Fixes

1. **Superseded list**: `config/tasks/productive_8h_superseded_tasks.yaml` → skip `superseded_task`
2. **Queue replacements**: 4 件を I5 低リスク docs タスクに差し替え（morning review / evidence CLI / runbook / discovery readonly）
3. **Safe Python markers**: `.py` の `change_file` には `# dev-loop smoke marker` コメント行を使用
4. **Pytest diagnostics**: `failed_tasks[].pytest_diagnostics`（cmd, exit, change_file, output_tail）

---

## 4. Next productive 8h expectations

- 旧 4 task は queue から削除 + superseded で二重ガード
- 同一 `pytest_failed` 連発は減る想定（診断行で原因特定が容易）
- I4 の budget 8 / category 4 / skip は変更なし
- dev-loop smoke marker: 20260523T035415Z (2026-05-23T04:02:12Z)
