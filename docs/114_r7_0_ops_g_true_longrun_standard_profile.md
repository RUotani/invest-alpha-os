# R7.0-Ops-G — true long-run standard profile

**日付**: 2026-05-20 · **性質**: `true_longrun_3h` profile + 運用スクリプト

---

## 1. 誤解の整理

| 事象 | 意味 |
|---|---|
| Cursor Agent が PR 実装を 10 分で終了 | long-run trial **ではない** |
| `overnight_safe_3h` のみ | **上限** 180 分；下限保証なし |
| `--max-tasks 1 --max-prs 1` | **smoke のみ** |

真の long-run = `true_longrun_3h` profile または `scripts/run_true_longrun_3h.sh`（Ops-F native flags 内蔵）。

---

## 2. Standard profile

`config/operator_dev_loop_profiles.yaml`:

- **`true_longrun_3h`**: min 180m、max tasks 50、max PRs 5、heartbeat after caps
- **`true_longrun_6h`**: min 360m（同上 caps）

`smoke_20min` / `overnight_safe_3h` は従来どおり（true long-run 非標準）。

---

## 3. One-command run

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
bash scripts/run_true_longrun_3h.sh
```

- dirty tree なら拒否
- auto-merge なし
- 終了時 `gh pr list`（merge しない）

---

## 4. Manual equivalent

```bash
operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue_longrun.yaml \
  --profile true_longrun_3h \
  --execute-dev-loop --create-pr --wait-ci \
  --max-tasks 50 --max-prs 5 \
  --stop-on-failure --stop-on-dirty-tree
```

（profile が min-runtime / no-early-success / continue-after を供給）

---

## 5. Prerequisite

- Ops-F merged: native `--min-runtime-minutes` / heartbeat behavior in `dev_loop`

---

## 6. Post-merge trial

merge 後、人間が `run_true_longrun_3h.sh` を実行。成功終了は `stop_reason=min_runtime reached: 180`、exit 0。
