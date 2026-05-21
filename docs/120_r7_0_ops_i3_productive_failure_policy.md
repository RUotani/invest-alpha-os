# R7.0-Ops-I3 — productive queue failure policy

**日付**: 2026-05-21 · **性質**: 非criticalタスク失敗時の継続と上限停止

---

## 1. Why I3 after I2

- I2: preflight（pytest/PATH/gates）で開始前に即停止
- 実運用: `ops_i_min_max_runtime_tests` 等の **1 task 失敗** で productive 8h 全体が `--stop-on-failure` により停止
- I3: 低リスク・非critical失敗は evidence に記録して次 task へ。critical / safety / 上限のみ停止

---

## 2. CLI（opt-in、デフォルトは従来どおり）

| フラグ | 意味 |
|---|---|
| `--continue-on-task-failure` | 非critical失敗を記録して継続 |
| `--max-task-failures N` | 記録失敗が N 到達で停止（continue 時デフォルト 3） |
| `--critical-task-failure-policy stop\|record` | critical は即停止（record は evidence に残して停止） |
| `--failure-summary` | 終了時に failed_tasks 要約を表示 |

`scripts/run_productive_true_longrun_8h.sh` は上記を有効化（`--stop-on-failure` は削除）。

---

## 3. Criticality

- YAML `critical: true/false` があれば優先
- なければ `risk_level` / `risk`: `high` / `critical` → critical
- `low` / `medium` → noncritical

---

## 4. Operator signals

| Signal | 種別 | Action |
|---|---|---|
| `PREFLIGHT FAILED` | 開始前 | env 修正、待たない |
| safety / dirty / forbidden | critical runtime | 即停止、修正後に再実行 |
| `productive-longrun task failed ... action=continue` | noncritical | 継続（run 後に evidence レビュー） |
| `max_task_failures reached: N` | 上限 | failed_tasks を確認してから再実行 |
| `SUCCEEDED_WITH_RECORDED_FAILURES` | 成功（失敗あり） | PR レビュー + failed_tasks 確認 |
| `min_runtime reached: 480` | 成功 | PR 人手レビュー |

---

## 5. Evidence

`evidence_summary.json` に `failure_policy` と `failed_tasks[]` を追加。
