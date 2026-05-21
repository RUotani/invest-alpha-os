# R7.0-Ops-I Cursor Longpack — Make 8h Long-Run Productive, Not Just Waiting

目的:
現在の `true_longrun_8h` は「8時間未満で正常終了しない」基盤としては正しい。
しかし、既存 `config/tasks/autonomous_dev_queue_longrun.yaml` は docs marker / runbook 系が中心で、実質的には短時間でPRを作成し、その後 heartbeat waiting になりやすい。
本PRでは、8時間枠をできる限り有効に使うため、task queue と runner policy を「実開発向け」に拡張する。

## Current problem

- `true_longrun_8h` has min_runtime 480m and visible heartbeat.
- But current longrun queue likely has only ~6 lightweight docs/marker tasks.
- Therefore the runner may:
  1. create several lightweight PRs quickly,
  2. hit task/PR caps or queue exhaustion,
  3. wait until min-runtime.
- This validates long-running behavior but does not maximize coding throughput.

## Target outcome

Create a productive 8h autonomous development mode that:
- has enough concrete implementation tasks to work through,
- prioritizes real product/dev improvements over marker docs,
- avoids unsafe auto-merge,
- avoids high-risk market/live/cache/Gmail actions,
- produces meaningful PRs with tests,
- uses heartbeat visibility,
- stops on real errors,
- does not merely wait unless the queue/caps are exhausted.

## Standard Agent Rules

Use token-saving mode: inspect files locally, do not print full files or full diffs, edit only minimal sections, and report only changed files, tests, CI, safety, failures, and next actions.

最終報告は、必ずワンクリックで全文コピー＆ペーストできる単一のMarkdownコードブロックで返してください。
通常文・表・箇条書きをコードブロック外に分散しないでください。

Do not intentionally run intermediate notification sounds. Do not run `afplay`, `say`, `osascript`, `terminal-notifier`, bell characters, or notification commands during intermediate steps.

## Hard Safety Rules

Do NOT:
- auto-merge
- force push
- delete branches
- delete worktrees
- push directly to main
- output secrets, `.env`, credentials, or tokens
- commit outputs or cache JSON
- run live HTTP without explicit gates
- write cache without explicit gates
- send Gmail without explicit gates
- change daily/signals defaults
- add trading recommendations, buy/sell wording, target prices, allocations
- connect portfolio / macro / Veto by default

## Required implementation

Create a new branch from latest `origin/main`.

Branch:
`work/r7-0-ops-i-productive-8h-queue`

PR title:
`R7.0-Ops-I: Add productive 8h autonomous task queue`

## 1. Add a productive task queue

Create:

`config/tasks/autonomous_dev_queue_productive_8h.yaml`

This queue must contain at least 12 tasks, prioritized and bounded.

The tasks should be low-to-medium risk and genuinely useful. Prefer product/dev improvements over docs-only marker tasks.

Suggested task categories:

### A. Operator usability / observability
1. Add a compact post-run summary command or helper for latest dev-loop evidence.
2. Improve evidence summary readability with stable keys and a concise terminal/table view.
3. Add stale/open PR cleanup guidance command in docs/script form, without auto-closing by default.
4. Add a `operator-runner status` or equivalent read-only subcommand if architecture makes this small and safe.

### B. Long-run robustness
5. Add tests for max_runtime vs min_runtime precedence and clear error/warning when min > max.
6. Add preflight warning if profile max_runtime < requested min_runtime.
7. Add profile validation for true_longrun profiles.
8. Add visible heartbeat test coverage for terminal output and evidence path.

### C. Discovery engine usefulness
9. Improve JP/US discovery output alignment if low-risk and cache-only.
10. Add discovery output summary docs/tests without live HTTP.
11. Add optional markdown table columns for reason labels / insufficient data counts if already supported.
12. Add read-only smoke command docs for discovery scan outputs.

### D. Daily/Gmail reporting polish, gated only
13. Improve Japanese daily email narrative templates in dry-run only.
14. Add docs/tests for no-attachment Gmail behavior if not already covered.
15. Add report preview summarizer with no live send.

Important:
- Each task must be independently scoped.
- Each task must define:
  - `task_id`
  - `title`
  - `risk`
  - `scope`
  - `prepare_for_pr`
  - `branch_template`
  - `change_files` or equivalent
  - `commit_message`
  - `tests`
  - `stop_conditions`
- Avoid tasks that require live HTTP, cache write, secrets, Gmail send, trading recommendations, or default behavior changes.

## 2. Add a productive 8h runner script

Add:

`scripts/run_productive_true_longrun_8h.sh`

Behavior:
- requires both gates:
  - `CONFIRM_OPERATOR_DEV_LOOP=YES`
  - `CONFIRM_GITHUB_PR_CREATE=YES`
- refuses dirty tree
- uses `caffeinate -dimsu`
- uses:
  - `--task-queue config/tasks/autonomous_dev_queue_productive_8h.yaml`
  - `--profile true_longrun_8h`
  - `--execute-dev-loop`
  - `--create-pr`
  - `--wait-ci`
  - `--max-tasks 100`
  - `--max-prs 10`
  - `--min-runtime-minutes 480`
  - `--no-early-success-exit`
  - `--heartbeat-interval-minutes 10`
  - `--continue-after-pr-limit heartbeat`
  - `--continue-after-task-limit heartbeat`
  - `--stop-on-failure`
  - `--stop-on-dirty-tree`
- logs to:
  - `outputs/operator/productive_true_longrun_8h/<RUN_ID>/run.log`
- must NOT auto-merge.

## 3. Add queue sufficiency preflight

Add a preflight warning or validation that prints:
- number of tasks in queue,
- number of executable/preparable tasks,
- max_tasks,
- max_prs,
- whether the queue is likely to exhaust before min_runtime.

Do not fail just because the queue may exhaust, but make it visible.

Example:
```text
productive-longrun preflight: tasks=15 max_tasks=100 max_prs=10 min_runtime=480m note=queue may exhaust before min_runtime; runner will heartbeat after exhaustion
```

## 4. Tests

Add tests for:
- productive queue exists and has >= 12 tasks.
- no task includes forbidden live/cache/Gmail/trading/default actions.
- productive script uses productive queue and true_longrun_8h.
- productive script includes both gates.
- queue sufficiency preflight emits task counts.
- existing true_longrun_8h behavior remains unchanged.

Do not run an actual 8h trial in this PR.

## 5. Docs

Add:
- `docs/118_r7_0_ops_i_productive_8h_queue.md`

Update:
- `docs/112_r7_0_ops_longrun_autonomous_runbook.md`
- `docs/01_development_status.md`

Docs must clearly distinguish:

### Infrastructure long-run
`bash scripts/run_true_longrun_8h.sh`
- proves 8h runtime behavior
- may wait after queue/cap exhaustion

### Productive long-run
`bash scripts/run_productive_true_longrun_8h.sh`
- uses larger practical development queue
- intended to spend more of the 8h window producing useful code/docs/tests PRs
- still may wait if queue/caps are exhausted
- auto-merge remains forbidden

## 6. PR

Create one PR only.
Do not merge automatically.

## Final report format

Return only one Markdown code block:

```markdown
## State Capsule — R7.0-Ops-I Productive 8h Queue

| item | value |
|---|---|
| branch | ... |
| start main | ... |
| commit | ... |
| PR | ... |
| CI | ... |

### Cause confirmed
- ...

### Changed files
- ...

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
