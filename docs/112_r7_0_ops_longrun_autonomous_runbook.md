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

## 9. Ops-H true_longrun_8h

8h run は **`true_longrun_8h`** + **`scripts/run_true_longrun_8h.sh`** のみ。`true_longrun_6h` は max 360m のため 8h に使わない。詳細 **[docs/117](./117_r7_0_ops_h_true_longrun_8h_heartbeat.md)**。

## 10. Ops-I productive 8h

実開発向け 16 task キュー: **`scripts/run_productive_true_longrun_8h.sh`**。詳細 **[docs/118](./118_ops_i_productive_8h_queue.md)**。

## 11. Ops-I2 fail-fast preflight

8h 開始前に pytest / gh / queue / gates を検証。失敗時は log + evidence + tail を表示。詳細 **[docs/119](./119_r7_0_ops_i2_productive_8h_failfast_preflight.md)**。

## 12. Ops-I3 productive failure policy

非critical task 失敗は記録して継続（上限 3）。critical/safety は即停止。詳細 **[docs/120](./120_r7_0_ops_i3_productive_failure_policy.md)**。

## 13. Ops-I4 failure budget + resume/skip

失敗上限 8、同一カテゴリ上限 4、既存 PR/branch skip。詳細 **[docs/121](./121_r7_0_ops_i4_failure_budget_resume_skip.md)**。

## 14. Ops-I5 repair productive queue failures

I4 後の pytest 4 連続失敗を queue 修復・superseded・診断強化。詳細 **[docs/122](./122_r7_0_ops_i5_repair_productive_queue_failures.md)**。

## 15. Ops-I6 productive 12h workday

12h 本命 runner: **`scripts/run_productive_true_longrun_12h.sh`** + `true_longrun_12h` + 32 task queue。詳細 **[docs/123](./123_r7_0_ops_i6_productive_12h_workday_profile.md)**。

## 16. Ops-I7 post-run review pipeline

`operator-runner post-run-review` / `merge_productive_prs_after_review.sh`（gate 必須）。v2 queue 草案。詳細 **[docs/124](./124_r7_0_ops_i7_post_run_review_pipeline.md)**。

## 17. Ops-I7B v2 queue scope

v2 先頭 task は `docs/125_ops_i7_v2_post_run_review_tests.md`（`docs/smoke.md` 禁止）。quarantine dirty 拒否。詳細 **[docs/125](./125_r7_0_ops_i7b_v2_queue_scope_fix.md)**。

## 18. Ops-I7C remove smoke fallback

productive は明示 `change_file` 必須。`docs/smoke.md` は実行前 quarantine 拒否。詳細 **[docs/126](./126_r7_0_ops_i7c_remove_smoke_fallback.md)**。

## 19. Ops-I7D v2 fixture scope

`docs/dev_loop_marker_fixture.md` と productive `docs/*fixture*.md` change_file を拒否。詳細 **[docs/127](./127_r7_0_ops_i7d_fix_v2_fixture_scope.md)**。

(dev-loop が実行時に marker 行を各 companion doc に追記)
- dev-loop smoke marker: 20260520T115316Z (2026-05-20T11:53:17Z)
- dev-loop smoke marker: 20260520T224502Z (2026-05-20T22:45:03Z)
