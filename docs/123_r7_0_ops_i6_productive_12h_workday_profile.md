# R7.0-Ops-I6 — productive 12h workday profile

**日付**: 2026-05-21 · **性質**: 10h 離席向け 12h productive autonomous run

---

## 1. Why 12h (not extended 8h only)

I5 run reached ~467m with **10 PRs** then **heartbeat_waiting** until `dev_loop_rc=130`. Extending 8h caps alone increases idle heartbeat time; 12h needs higher **max_prs (25)**, **max_tasks (40)**, and a **~32 task queue**.

---

## 2. Command

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_productive_true_longrun_12h.sh
```

Profile: `true_longrun_12h` (min **720m**, max **750m**). Log: `outputs/operator/productive_true_longrun_12h/<RUN_ID>/run.log`.

---

## 3. Outcomes

| Banner | Meaning |
|---|---|
| `SUCCEEDED` | min_runtime reached (720m) |
| `SUCCEEDED_WITH_RECORDED_FAILURES` | completed with failed/skipped tasks recorded |
| `INTERRUPTED_AFTER_PRODUCTIVE_CAP` | rc 130 near min_runtime after PR/task cap + heartbeat (often acceptable) |
| `FAILED: max_task_failures` | fix env/tasks before rerun |
| `FAILED: max_same_failure_category` | same pytest cluster — repair queue (see I5) |

---

## 4. Morning review

1. Read `run.log` and latest `evidence_summary.json`
2. Metrics: `tasks_seen`, `tasks_executed`, `prs_created`, `failed_tasks`, `skipped_tasks`, `longrun.elapsed_minutes`
3. `gh pr list --state open` — merge green PRs; close superseded duplicates
4. `git checkout main && git pull` — clean tree before next run

---

## 5. Utilization note

After **max_prs** or queue exhaustion, runner **heartbeats** until min_runtime. Review **prs_created** and **tasks_executed**, not heartbeat duration alone.
