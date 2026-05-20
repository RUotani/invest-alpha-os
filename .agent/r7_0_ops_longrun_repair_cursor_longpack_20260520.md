# R7.0-Ops Long-Run Repair Pack — true bounded autonomous run

Purpose: Fix the previous failure mode where Cursor/operator-runner stopped too early because the run was configured as `--max-tasks 1 --max-prs 1` and the queue contained a fast docs/status microfix. This pack shifts the operation to a real long-run profile: multiple meaningful tasks, higher PR cap, no stop after first success, strict safety gates, evidence-first reporting, and auto-merge forbidden.

## Critical correction

The prior command was not a 3-hour run. `overnight_safe_3h` is only an upper runtime profile; it does not force the runner to keep working for 3 hours. If `--max-tasks 1`, `--max-prs 1`, or a queue with only tiny docs/status tasks is used, the runner will legitimately stop early.

Do not run the old pattern:

```bash
--max-tasks 1 --max-prs 1
```

For a real long-run, use:

```bash
--max-runtime-minutes 180 --max-tasks 6 --max-prs 3
```

or, if the current CLI does not expose `--max-runtime-minutes`, keep the `overnight_safe_3h` profile and use:

```bash
--max-tasks 6 --max-prs 3
```

The queue must contain meaningful work, not repeated docs/status microfix only.

---

## Paste target

Paste the following into **Cursor Agent**, not Terminal.

---

## Cursor Agent instruction

You are working in the local repository:

```text
/Users/uotani/Projects/invest-alpha-os
```

Use token-saving mode: inspect files locally, do not print full files or full diffs, edit only minimal sections, and report only changed files, tests, CI, safety, failures, and next actions.

Final report must be returned as one copy-pasteable Markdown code block only. Do not scatter normal prose, tables, or bullet lists outside the code block.

### Goal

Repair the autonomous long-run setup so that the next run is a genuine bounded long-run, not an early one-task/one-PR stop. The expected behavior is to keep progressing through multiple safe tasks until one of these happens:

- max runtime is reached,
- max tasks is reached,
- max PRs is reached,
- failure or dirty tree stop condition triggers,
- CI failure/pending timeout triggers.

### Current problem to fix

The previous run stopped early because the effective instruction pattern was too small:

- `--max-tasks 1`
- `--max-prs 1`
- queue biased toward quick docs/status microfix
- PR creation immediately satisfied the stop condition

This is not an overnight/3-hour run. Treat this as a design/operations bug in the runbook and task queue, not as success.

### Required implementation scope

Create a focused PR that makes long-run behavior explicit and harder to misuse.

Implement the smallest safe set of changes needed to support and document a true long-run mode.

Prefer these files if they exist:

- `config/tasks/autonomous_dev_queue.yaml`
- `config/tasks/*long*queue*.yaml`
- `docs/*operator*`
- `docs/*ops*`
- `docs/01_development_status.md`
- `.agent/*longpack*.md`
- operator-runner tests under `tests/`

You may create a new queue file if cleaner, for example:

```text
config/tasks/autonomous_dev_queue_longrun.yaml
```

### Required behavior / acceptance criteria

1. Add or update a long-run task queue that contains multiple safe, meaningful tasks.
   - Do not make the queue only `docs_status_microfix` repeated.
   - Include at least 3 to 6 bounded tasks.
   - Tasks should be low-risk and self-contained.
   - Prefer practical improvements such as:
     - PR body quality improvement,
     - evidence summary readability,
     - stop_reason classification docs/tests,
     - runbook/status consistency checks,
     - operator-runner reporting polish,
     - queue validation / safety validation tests.

2. Add a runbook section that clearly says:
   - `overnight_safe_3h` is an upper bound, not a minimum runtime guarantee.
   - `--max-tasks 1 --max-prs 1` is a smoke test only.
   - true long-run should use `--max-tasks 6 --max-prs 3`, or equivalent.
   - the runner can still stop early only for explicit stop reasons.

3. Add a safe command template for true long-run:

```bash
cd /Users/uotani/Projects/invest-alpha-os
git fetch origin main --prune
git checkout -B main-sync-longrun-next origin/main

CONFIRM_OPERATOR_DEV_LOOP=YES \
CONFIRM_GITHUB_PR_CREATE=YES \
.venv/bin/python -m invis_alpha_os.cli.main operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue_longrun.yaml \
  --profile overnight_safe_3h \
  --execute-dev-loop \
  --create-pr \
  --wait-ci \
  --max-tasks 6 \
  --max-prs 3 \
  --stop-on-failure \
  --stop-on-dirty-tree

git status --short
gh pr list --state open --limit 10
```

If `config/tasks/autonomous_dev_queue_longrun.yaml` is not created, use the actual queue path you created/updated.

4. Add tests where appropriate.
   - Test that the long-run queue has multiple tasks.
   - Test that the runbook/queue does not encode the old smoke-only pattern as the standard.
   - Test branch naming and safety behavior only if adjacent test patterns already exist.

5. Run local checks:

```bash
git diff --check
.venv/bin/python -m pytest -q tests/test_operator_runner*.py tests/test_operator_pr_loop.py || true
```

If the broad operator test glob is too broad or unavailable, run the nearest relevant tests and report exactly what ran.

### Safety constraints — must not violate

Do not perform any of the following:

- main direct push
- force push
- branch deletion
- worktree deletion
- auto-merge
- `gh pr merge`
- `gh pr close`
- secrets / `.env` / token / credentials output
- credentials / token / env commit
- cache JSON commit
- outputs commit
- ungated live HTTP
- ungated cache write
- ungated Gmail send
- daily / signals default behavior changes
- trading recommendation / buy / sell / target price / allocation
- portfolio / macro / Veto connection changes

### Allowed GitHub action

You may create a PR if all gates and tests pass.

Use branch naming like:

```text
work/r7-0-ops-longrun-repair
```

Suggested title:

```text
R7.0-Ops: Repair autonomous long-run queue and runbook
```

PR body must include:

- why the previous pattern stopped early,
- new long-run command,
- tests run,
- safety confirmation,
- remaining manual next action.

Do not merge the PR. Human merge only.

### Stop conditions

Stop and report if any of these occur:

- working tree is dirty before starting and changes are unrelated,
- tests fail and cannot be safely fixed surgically,
- CI fails,
- command option does not exist and requires product-code redesign,
- task queue schema is unclear,
- a requested change would require live HTTP, cache write, Gmail send, or default investment signal changes.

### Final report format

Return exactly one Markdown code block with this structure:

```markdown
## State Capsule — R7.0-Ops Long-Run Repair

| item | value |
|---|---|
| branch | ... |
| start main | ... |
| commit | ... |
| PR | ... |
| CI | ... |

### Changed files
- ...

### What changed
- ...

### Long-run correction
- Previous early stop cause: ...
- New standard queue: ...
- New standard caps: ...

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
