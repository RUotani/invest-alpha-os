# R7.0-Ops-I7 — post-run review pipeline

**日付**: 2026-05-21 · **性質**: 12h 成功後の朝レビュー標準化 + v2 queue 草案

---

## 1. I6 result (confirmed)

- run `20260521T223933Z`: `longrun_exit_success=true`, `min_runtime reached: 720`
- PRs **#115–#132** created and merged → main `e4b44df`

---

## 2. Commands

### Post-run review (read-only)

```bash
operator-runner post-run-review --run-id 20260521T223933Z --format markdown
# or
bash scripts/review_productive_longrun.sh 20260521T223933Z
```

### Gated merge (human only)

```bash
export CONFIRM_PRODUCTIVE_PR_MERGE=YES
bash scripts/merge_productive_prs_after_review.sh --prs 115-132
```

No autonomous merge. Stops on first failed check or merge error.

---

## 3. Productive 12h v2 queue (draft)

- `config/tasks/autonomous_dev_queue_productive_12h_v2.yaml` (~32 tasks)
- Mix: tests / small impl / docs — **not wired** into default runners yet
- Enable only after operator review of v2 task list

---

## 4. Morning flow

1. `post-run-review` (latest or explicit run_id)
2. `gh pr list --state open`
3. Check CI on merge candidates
4. Gated merge helper or manual squash merge
5. `git fetch && git pull` on main
6. Confirm clean tree before next `run_productive_true_longrun_12h.sh`
