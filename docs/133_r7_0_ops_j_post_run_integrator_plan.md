# R7.0-Ops-J — Post-run Integrator (plan)

**Goal**: After productive longrun, minimize human triage/merge work for stacked PR batches.

## Problem (I11 run `20260523T112747Z`)

- 18 minutes wall time, `early_completion: pr_cap_reached`, 15/84 tasks, 15 PRs (#185–#199).
- PRs are **stacked** (each includes prior commits). Sequential squash-merge of #185 made #186+ **BEHIND**.
- Repo disallows merge commits; squash-only.

## Proposed CLI

```bash
.venv/bin/python -m invis_alpha_os.cli.main operator-runner post-run-integrate \
  --run-id 20260523T112747Z \
  --pr-range 185-199 \
  --dry-run
```

### Phases (read-only default)

1. **audit** — load evidence + `gh pr view` for range; risk class; `safe_auto_merge_candidate`.
2. **strategy** — if stacked and BEHIND after first merge → **consolidation** (single PR from tip branch vs `origin/main`).
3. **integrate** (gated) — requires `CONFIRM_PRODUCTIVE_PR_MERGE=YES`; squash merge or open consolidation PR; never `--auto`.
4. **report** — markdown summary + optional macOS notify (best-effort).

### Gates (integrate mode)

- OPEN, not draft, checks SUCCESS, mergeStateStatus CLEAN (or consolidation path).
- Paths: `docs/`, `tests/`, `scripts/` only (configurable).
- Block: workflows, `pyproject.toml`, `Makefile`, `src/` product changes, secrets.

### I11 resolution applied

- Merged #185 (squash).
- Opened consolidation PR for remaining diff from PR #199 tip vs `main`.
- Close #186–#199 as superseded (branches retained).

## Next implementation slices

1. `post_run_integrate.py` + CLI wiring (dry-run audit only).
2. Consolidation branch builder (`git diff origin/main...pr_tip`).
3. Optional: `max_prs` adaptive from historical skip/velocity (queue v4).
