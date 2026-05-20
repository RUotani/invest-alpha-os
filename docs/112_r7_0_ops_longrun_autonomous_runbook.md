# R7.0-Ops — bounded long-run autonomous runbook

**日付**: 2026-05-20 · **性質**: true long-run（複数 task / 複数 PR）運用

---

## 1. Critical correction

| 誤解 | 事実 |
|---|---|
| `overnight_safe_3h` = 3時間必ず動く | **上限**（max runtime）のみ。早く止まるのは正常 |
| `--max-tasks 1 --max-prs 1` = 夜間本番 | **smoke / mini trial のみ** |
| docs microfix 1件だけの queue = long-run | **早期停止が正しい**（設計バグではない） |

早期停止の典型原因: `max_tasks` / `max_prs` が 1、queue が単一 docs task のみ、最初の PR 成功で `max_prs` 到達。

---

## 2. Standard long-run caps

`overnight_safe_3h` profile と合わせて CLI override:

- `--max-tasks 6`（profile 既定と同値可）
- `--max-prs 3`
- `--max-runtime-minutes 180`（profile 既定、明示可）
- `--wait-ci`（profile で `wait_ci: true`）

**禁止パターン（本番 long-run）**: `--max-tasks 1 --max-prs 1`

---

## 3. Queue

- **Long-run**: `config/tasks/autonomous_dev_queue_longrun.yaml`（6 tasks、docs-only prepare）
- **Smoke / mixed**: `config/tasks/autonomous_dev_queue.yaml`（mini trial・混在検証用）

---

## 4. Guarded long-run command

```bash
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES

operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue_longrun.yaml \
  --profile overnight_safe_3h \
  --execute-dev-loop \
  --create-pr \
  --wait-ci \
  --max-tasks 6 \
  --max-prs 3 \
  --stop-on-failure \
  --stop-on-dirty-tree
```

---

## 5. Explicit stop reasons（継続条件）

runner は次のいずれかまで進む（早停のみ）:

- `max_runtime reached`
- `max_tasks reached`
- `max_prs reached`
- task failure / dirty tree / safety validator
- CI wait timeout / failure

---

## 6. Safety

- auto-merge 禁止
- force push / branch 削除禁止
- merge は人間判断

---

## 7. Ops-F native mode

cap 到達後も `min_runtime` まで heartbeat: **[docs/113](./113_r7_0_ops_f_native_true_longrun_mode.md)**。

## 8. Ops-G2 standard profile（推奨）

運用標準: **`true_longrun_3h`** + **`scripts/run_true_longrun_3h.sh`**。詳細 **[docs/114](./114_r7_0_ops_g2_recovered_true_longrun_profile.md)**。

(dev-loop が実行時に marker 行を各 companion doc に追記)
- dev-loop smoke marker: 20260520T115316Z (2026-05-20T11:53:17Z)
