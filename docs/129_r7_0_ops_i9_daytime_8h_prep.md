# R7.0-Ops-I9 — Daytime 8h productive preparation and run

**日付**: 2026-05-23 · **main**: `fcaa686` · **prep PR**: #166

---

## 1. Goals delivered (G1–G4)

| goal | deliverable |
|---|---|
| G1 | `scripts/list_productive_stacked_prs.sh` · consolidation guidance below |
| G2 | `pytest_no_tests_collected` category for pytest exit 5 |
| G3 | `run_productive_true_longrun_8h.sh` — preflight `exit 2`, `STOP` + final `exit dev_loop_rc` |
| G4 | `.agent/r7_0_ops_i10_night_12h_v2_longpack.md` skeleton |

---

## 2. When to consolidate vs merge (#165 pattern)

**Merge individually** when: few open PRs, each CI green, no stacked branch conflicts.

**Consolidate** (#165-style) when:

- Many open PRs share `work/dev-loop/autonomous/` prefix
- Later PRs would conflict after squash-merge of an earlier sibling
- Net diff from last stacked PR is the desired final state

Steps:

1. `bash scripts/list_productive_stacked_prs.sh`
2. Close obsolete stacked PRs (#140–#163 pattern) after consolidation PR merges
3. One PR onto `origin/main` with net diff — no force push

---

## 3. Daytime 8h run (not 12h)

```bash
export PATH="$(pwd)/.venv/bin:$PATH"
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
export PRODUCTIVE_QUEUE=config/tasks/autonomous_dev_queue_productive_8h_i9.yaml
bash scripts/run_productive_true_longrun_8h.sh
```

Evidence: `outputs/operator/productive_true_longrun_8h/<RUN_ID>/run.log`

---

## 4. pytest `-k` exit 5

- Exit **5** = no tests collected → category **`pytest_no_tests_collected`**
- Prefer file-level `pytest_cmd` or stable test names over brittle `-k` in productive queues
- Superseded: `ops_i_profile_runtime_warning` (see `productive_8h_superseded_tasks.yaml`)
- dev-loop smoke marker: 20260523T035415Z (2026-05-23T03:57:41Z)
