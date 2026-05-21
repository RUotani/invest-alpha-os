# R7.0-Ops-H — true_longrun_8h and visible heartbeat

**日付**: 2026-05-20 · **性質**: 8h min-runtime profile + terminal heartbeat

---

## 1. Why previous 8h attempt stopped at 360m

- `--min-runtime-minutes 480` を指定しても **`--profile true_longrun_6h`** を使うと `max_runtime_minutes: 360` が上限
- 結果: `stop_reason=max_runtime reached: 360m`（6h profile で 8h は不可）

**`true_longrun_6h` を 8h run に使わない。**

---

## 2. true_longrun_8h profile

| 項目 | 値 |
|---|---|
| min_runtime_minutes | 480 |
| max_runtime_minutes | 510（min より大きい overhead） |
| max_tasks | 100 |
| max_prs | 10 |
| no_early_success_exit | true |
| heartbeat_interval_minutes | 10 |

---

## 3. Standard command

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_true_longrun_8h.sh
```

- `caffeinate -dimsu`（macOS）
- log: `outputs/operator/true_longrun_8h/<RUN_ID>/run.log`
- auto-merge 禁止

---

## 4. Visible heartbeat

約 10 分ごとに terminal へ 1 行（例）:

```text
true-longrun heartbeat: utc=... elapsed=240.0m remaining=240.0m min_runtime=480m state=heartbeat_waiting prs=10 tasks=10 evidence=outputs/operator/dev_loop/<run_id>/evidence_summary.json
```

---

## 5. Expected success

- `stop_reason=min_runtime reached: 480`
- exit 0

---

## 6. vs true_longrun_3h / 6h

- **3h**: `scripts/run_true_longrun_3h.sh` / profile `true_longrun_3h`
- **6h**: max 360m min-runtime — **not** for 8h
- **8h**: 本 PR の profile + script
