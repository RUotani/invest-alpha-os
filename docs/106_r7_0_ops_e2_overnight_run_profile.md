# R7.0-Ops-E2 — overnight run profile and guarded PR-create smoke

**日付**: 2026-05-20 · **main 起点**: `5fdf040` · **性質**: dev-loop run profile と runbook 追加

---

## 1. Purpose

`dev-loop` の夜間運用に向け、再現可能な run profile と guarded 実行手順を整備する。

---

## 2. Profiles

`config/operator_dev_loop_profiles.yaml`:

- `smoke_20min`
- `overnight_safe_3h`
- `overnight_safe_6h`

各 profile は `max_runtime_minutes`, `max_tasks`, `max_prs`, `wait_ci`, `ci_timeout_seconds`, `ci_poll_seconds`, `stop_on_failure`, `stop_on_dirty_tree` を保持。

---

## 3. CLI usage

- profile 指定:
  - `alpha-os operator-runner dev-loop --profile smoke_20min`
- override:
  - `--profile overnight_safe_3h --max-tasks 2 --max-prs 1`
- 実行ゲート:
  - `--execute-dev-loop` + `CONFIRM_OPERATOR_DEV_LOOP=YES`
- PR作成ゲート:
  - `--create-pr` + `CONFIRM_GITHUB_PR_CREATE=YES`

---

## 4. Guarded smoke run (terminal paste)

```bash
.venv/bin/python -m invis_alpha_os.cli.main operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue.yaml \
  --profile smoke_20min \
  --execute-dev-loop \
  --max-tasks 1 \
  --max-prs 1 \
  --stop-on-failure \
  --stop-on-dirty-tree
```

---

## 5. Morning checklist

- evidence path（`outputs/operator/dev_loop/<run_id>/evidence_summary.json`）
- created PR count / PR URL一覧
- CI結果（`ci_wait_status`）
- `git status --short`
- final `stop_reason`
- merge は人間判断（auto-merge 禁止）

---

## 6. Safety notes

- 自動 merge 禁止を維持
- live/cache/send/default/trading の禁止方針を維持
- profile で無制限実行は許可しない
