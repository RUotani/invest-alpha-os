# R7.0-Ops-I9 Cursor Longpack — Daytime 8h Productive Preparation

目的:
I8（#165 consolidated v2 outputs + #164 automation contract）完了後、**昼間枠の productive 8h** を安全に再開できるよう準備する。

**本 Longpack は 8h 実 run を開始しない。** 人間が明示指示するまで `bash scripts/run_productive_true_longrun_8h.sh` を実行しない。

準拠: `.agent/development_automation_contract.md` · `.agent/standard_clauses.md` · `.agent/safety_rules.md`

---

## Current state (start I9)

| item | value |
|---|---|
| main | `355da8a` |
| open PR | none |
| main CI | success |
| I8 | complete — see `.agent/r7_0_ops_i8_completion_state_capsule.md` |
| 8h entrypoint | `scripts/run_productive_true_longrun_8h.sh` |
| 8h queue | `config/tasks/autonomous_dev_queue_productive_8h.yaml` |
| 8h profile | `true_longrun_8h` in `config/operator_dev_loop_profiles.yaml` |
| 12h v2 (night) | `autonomous_dev_queue_productive_12h_v2.yaml` — **out of scope for I9 execution**; draft next-night pack only |

---

## I9 goals (preparation only)

### G1 — Stacked PR consolidation recovery

Harden the post–long-run workflow so a v2-style stacked PR pile does not require manual conflict archaeology.

Deliverables (code/docs/tests as needed):

- Document **when to consolidate** vs merge individual PRs (runbook section in new `docs/129_*` or extend `docs/124`).
- Optional helper script or `operator-runner` subcommand sketch: list open PRs by branch prefix / task_id, suggest consolidation branch name.
- Tests or docs for **#165-style** flow: net diff from last stacked PR onto current `origin/main` without force push.
- Reference closed **#140–#163** as obsolete-after-consolidation pattern in State Capsule template.

### G2 — pytest `-k` no-match exit 5

Productive tasks using `pytest -q ... -k <expr>` must not destabilize the queue when **0 tests match** (pytest exit code **5**).

Deliverables:

- **Fix or document** in `dev_loop.py` / failure policy: treat exit 5 as `pytest_no_tests_collected` (recoverable or supersede), not opaque `pytest_failed`.
- Extend `config/tasks/productive_8h_superseded_tasks.yaml` or queue tasks that still use brittle `-k` selectors.
- Tests: `tests/test_operator_dev_loop.py` — exit 5 classification, continue-on-failure budget behavior.
- Docs: when to avoid `-k` in productive queues; prefer file-level or stable test names.

### G3 — Terminal-safe commands (no `exit 1` in user-facing loops)

Shell scripts and operator-facing loops must not use **`exit 1`** in paths the human runs repeatedly (preflight, status checks, tail loops). Use:

- `preflight_fail` with message + **`exit 2`** or dedicated codes documented in runbook, **or**
- `if ! cmd; then echo "FAIL: ..."; FAILED=1; fi` and single exit at end.
- **`set +e`** only where explicitly documented with aggregation.

Audit targets:

- `scripts/run_productive_true_longrun_8h.sh`
- `scripts/run_productive_true_longrun_12h.sh` (read-only pattern sync if applicable)
- `scripts/review_productive_longrun.sh` · `scripts/merge_productive_prs_after_review.sh`
- any new I9 helper scripts

### G4 — Prepare next night long-run pack (12h v2)

Draft only (file under `.agent/`, no 12h run):

- `.agent/r7_0_ops_i10_night_12h_v2_longpack.md` (skeleton): queue v2 post-I8 main, superseded list refresh, consolidation preflight, min 720m, post-run review gate.

### G5 — Safety boundaries (unchanged)

Forbidden without explicit Longpack approval:

- auto-merge · force push · branch/worktree deletion · main direct push
- secrets / `.env` / credentials in output or commits
- outputs / cache JSON commits
- live HTTP · cache write · Gmail send
- daily/signals default changes
- trading recommendation / buy/sell / target price / allocation wording
- Veto / portfolio / macro default connection
- changes to `Makefile` / `pyproject.toml` / `.github/workflows/*` unless explicitly approved

---

## Required branch / PR (I9 implementation phase)

Create from latest `origin/main` after human approves prep work start.

| item | value |
|---|---|
| branch | `work/r7-0-ops-i9-daytime-8h-prep` |
| PR title | `R7.0-Ops-I9: Daytime 8h productive preparation` |

One PR only. Do not auto-merge.

---

## Standard Agent Rules

Token-saving mode: inspect locally; minimal diffs; no full files/diffs/logs in chat.

最終報告は **単一 Markdown コードブロック** のみ（`.agent/report_template.md`）。

Do not run intermediate notification sounds.

---

## Phase plan (I9)

### Phase 0 — setup (this session may stop after file creation)

- Confirm main `355da8a`, no open PRs, CI success
- Confirm `.agent/development_automation_contract.md` present
- `git status --short` — report clean/dirty
- **Do not commit** until human requests

### Phase 1 — analysis (read-only)

Targeted grep only:

```bash
grep -R "exit 1\|exit 5\|pytest_failed\|consolidat\|-k " scripts src config/tasks docs .agent | head -120
```

Read minimally:

- `src/invis_alpha_os/operator/dev_loop.py` (failure categories, pytest diagnostics)
- `scripts/run_productive_true_longrun_8h.sh`
- `config/tasks/autonomous_dev_queue_productive_8h.yaml`
- `config/tasks/productive_8h_superseded_tasks.yaml`
- `docs/124_r7_0_ops_i7_post_run_review_pipeline.md`

### Phase 2 — implementation

1. G1–G3 code/docs/tests per goals above
2. Add `docs/129_r7_0_ops_i9_daytime_8h_prep.md`
3. Update `docs/01_development_status.md` · `docs/112_r7_0_ops_longrun_autonomous_runbook.md`
4. Create draft `.agent/r7_0_ops_i10_night_12h_v2_longpack.md` (skeleton only)
5. Optional: refresh productive 8h queue tasks if I8 merge left stale definitions (minimal)

### Phase 3 — verification (no 8h run)

```bash
git diff --check
.venv/bin/python -m pytest -q tests/test_operator_dev_loop.py tests/test_operator_post_run_review.py
# plus any new targeted tests
```

Do **not** run:

- `bash scripts/run_productive_true_longrun_8h.sh`
- 12h v2 productive run
- live HTTP / cache write / Gmail send

---

## 8h run checklist (human — after I9 merge + explicit go)

Only when human says start 8h:

```bash
export PATH="/Users/uotani/Projects/invest-alpha-os/.venv/bin:$PATH"
export CONFIRM_OPERATOR_DEV_LOOP=YES
export CONFIRM_GITHUB_PR_CREATE=YES
# clean tree required
bash scripts/run_productive_true_longrun_8h.sh
```

Preflight must show `PRODUCTIVE-LONGRUN-8H` gates ok. Evidence under `outputs/operator/productive_true_longrun_8h/<RUN_ID>/`.

---

## Final report format

```markdown
## State Capsule — R7.0-Ops-I9 Daytime 8h Prep

| item | value |
|---|---|
| branch | ... |
| start main | 355da8a |
| commit | ... |
| PR | ... |
| CI | ... |

### Implemented
- ...

### Tests
- ...

### Safety
- ...

### Failures / caveats
- ...

### Next actions
1. ...
2. ...
3. ...
```

Max 3 next actions. No prose outside the code block.
