# R7.0-Ops-I11 — longrun utilization analysis

**日付**: 2026-05-23 · **目的**: 8h/12h productive run の実効利用率を evidence から逆算し、v3 queue 設計に反映する。

---

## 1. Runs inspected（local `outputs/operator/`）

| run_id | queue / profile | seen | executed | PRs | skipped | elapsed (m) | early | notes |
|---|---|---:|---:|---:|---:|---:|---|---|
| 20260523T035415Z | 8h i9 / true_longrun_8h | 8 | 8 | 8 | 0 | 292 | no | 実作業 ~9m 後 `heartbeat_waiting`（I9） |
| 20260523T094524Z | 12h v2 / true_longrun_12h_bounded | 32 | 6 | 5 | 26 | 6.0 | yes | `existing_pr` skip 26、early_completion |
| 20260522T142443Z | 12h v2 / true_longrun_12h | 32 | 26 | 25 | 1 | 720 | no | 耐久寄り・min_runtime 完走 |
| 20260521T223933Z | 12h / true_longrun_12h | 32 | 18 | 18 | 14 | 720 | no | skip 14 `existing_pr` |
| 20260521T143352Z | 8h productive | 16 | 11 | 10 | 4 | 473 | no | heartbeat 待ち |

---

## 2. Metrics

| 指標 | I9 8h | I10 12h v2 (bounded) | I6 12h (durability) |
|---|---:|---:|---:|
| Task utilization (executed/seen) | 100% | 19% | 56% |
| Skip rate | 0% | 81% | 44% |
| PRs / elapsed (per hour) | ~52/h（6m で 8） | ~50/h（6m で 5） | ~1.5/h（12h で 18） |
| Heartbeat / wait waste | ~283m after work done | ~714m remaining at early exit | 意図的 min_runtime |

**Skip breakdown (I10 v2)**: 26/26 = `existing_pr`（v2 queue の PR/branch が既に open/merged）。

---

## 3. Conclusions

1. **I9**: 実作業は短いが `no_early_success_exit` で長時間 heartbeat のみ（I10 で early_completion 解消）。
2. **I10 v2 bounded**: early_completion は成功したが、**queue が薄い**（再利用タスクが既存 PR に吸収され skip 偏重）。
3. **次回 v3**: primary / reserve / stretch の **84 候補**、新規 `task_id` + `pr_title`、`max_prs` 15、`max_tasks` 72、early_completion + notify。
4. **耐久試験**と **productive completion run** は profile/queue で分離（v3 は productive 専用）。

---

## 4. References

- v3 queue: `config/tasks/autonomous_dev_queue_productive_12h_v3.yaml`
- Runner: `scripts/run_productive_true_longrun_12h_v3.sh`
- Profile: `true_longrun_12h_productive_v3`
- I10 early completion: `docs/130_r7_0_ops_i10_early_completion_notification.md`
- dev-loop smoke marker: 20260523T112747Z (2026-05-23T11:27:48Z)
