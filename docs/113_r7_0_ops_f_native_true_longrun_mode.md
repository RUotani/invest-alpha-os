# R7.0-Ops-F — native true long-run mode

**日付**: 2026-05-20 · **性質**: runner 内蔵 min-runtime / heartbeat（supervisor 非依存）

---

## 1. Problem

- `max_prs reached` / `max_tasks reached` は上限到達であり、致命的エラーではない
- 外側 shell が `dev_loop_rc=1` を failure 扱いすると誤停止
- `--max-tasks 1 --max-prs 1` は smoke のみ

---

## 2. Native long-run flags

| Option | 役割 |
|---|---|
| `--min-runtime-minutes` | 成功終了までの最低稼働時間 |
| `--no-early-success-exit` | cap 到達後も即終了しない（要 min-runtime） |
| `--heartbeat-interval-minutes` | heartbeat 間隔（既定 10） |
| `--continue-after-pr-limit` | `wait` / `heartbeat` / `next-cycle` / `stop` |
| `--continue-after-task-limit` | 同上 |

省略時は **従来どおり**（cap で `stopped`、exit 1）。

---

## 3. Exit code

| 状況 | exit |
|---|---|
| `min_runtime reached` | 0 |
| real failure（dirty tree / task_failed / blocked） | 1 |
| cap のみ（long-run オフ） | 1 |

---

## 4. Evidence `longrun` block

`longrun_state`: `cap_reached_waiting` | `heartbeat_waiting` | `min_runtime_reached` | `controlled_stop`

---

## 5. Post-merge command（3h 実行は人間判断）

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES

operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue_longrun.yaml \
  --profile overnight_safe_3h \
  --execute-dev-loop \
  --create-pr \
  --wait-ci \
  --max-tasks 50 \
  --max-prs 5 \
  --min-runtime-minutes 180 \
  --no-early-success-exit \
  --heartbeat-interval-minutes 10 \
  --continue-after-pr-limit heartbeat \
  --continue-after-task-limit heartbeat \
  --stop-on-failure \
  --stop-on-dirty-tree
```

`overnight_safe_3h` は **上限** のみ。true long-run には上記 native flags が必要。
