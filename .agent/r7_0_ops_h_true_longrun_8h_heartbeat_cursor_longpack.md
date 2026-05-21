# R7.0-Ops-H Cursor Longpack — Add true_longrun_8h and Visible Heartbeat

目的:
前回の「8時間run」は `--min-runtime-minutes 480` を指定したが、`--profile true_longrun_6h` の max_runtime=360m が安全上限として効き、6時間で正常停止した。
これを修正し、正式な `true_longrun_8h` profile と、無音に見えない terminal heartbeat 表示を追加する。

## Current confirmed state

- #70 merged: native true long-run flags
- #72 merged: recovered true long-run standard profile
- true_longrun_3h completed successfully:
  - `stop_reason=min_runtime reached: 180`
  - 5 PRs created
- #73-#77 merged and main CI green
- A later long run using `true_longrun_6h` created #78-#83 and stopped with:
  - `stop_reason=max_runtime reached: 360m`
  - reason: `true_longrun_6h` max_runtime was 360 minutes
- #78-#83 have been merged
- latest known main after merge: `6d73a52`
- main CI should be confirmed green before starting this pack

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
`work/r7-0-ops-h-true-longrun-8h-heartbeat`

PR title:
`R7.0-Ops-H: Add true 8h long-run profile and visible heartbeat`

### 1. Add true_longrun_8h profile

Update `config/operator_dev_loop_profiles.yaml`.

Add:

```yaml
true_longrun_8h:
  description: "True 8-hour autonomous development run with no early success exit."
  max_runtime_minutes: 510
  min_runtime_minutes: 480
  no_early_success_exit: true
  heartbeat_interval_minutes: 10
  continue_after_pr_limit: heartbeat
  continue_after_task_limit: heartbeat
  max_tasks: 100
  max_prs: 10
```

Notes:
- `min_runtime_minutes` must be 480.
- `max_runtime_minutes` must be >= 480. Prefer 510 to allow small overhead.
- Do not reuse `true_longrun_6h` for 8h runs.
- Keep smoke profiles unchanged.

### 2. Add standard 8h script

Add executable:

`scripts/run_true_longrun_8h.sh`

Behavior:
- requires:
  - `CONFIRM_OPERATOR_DEV_LOOP=YES`
  - `CONFIRM_GITHUB_PR_CREATE=YES`
- refuses dirty tree before start
- uses `caffeinate -dimsu`
- logs to:
  - `outputs/operator/true_longrun_8h/<RUN_ID>/run.log`
- runs:
  - `operator-runner dev-loop`
  - `--task-queue config/tasks/autonomous_dev_queue_longrun.yaml`
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
- must NOT merge PRs
- final output should list open PRs and latest evidence path if possible

### 3. Add visible heartbeat output

Current long-run is operationally confusing because terminal may look frozen.

Implement visible heartbeat in either:
- `dev_loop.py` long-run wait loop, or
- the wrapper script if easier and safe

Required terminal heartbeat content every heartbeat interval:
- current UTC time
- elapsed minutes
- min_runtime_minutes
- remaining minutes
- longrun_state
- prs_created
- tasks_executed
- evidence path

Example line:

```text
true-longrun heartbeat: elapsed=240.0m remaining=240.0m state=heartbeat_waiting prs=10 tasks=10 evidence=outputs/operator/dev_loop/<run_id>/evidence_summary.json
```

Important:
- Do not spam every second.
- 10-minute interval is enough.
- Tests should use fake clock or small intervals; do not sleep for real long periods.

### 4. Tests

Add/update tests for:
- `true_longrun_8h` profile resolves:
  - min_runtime=480
  - max_runtime>=480
  - no_early_success_exit=true
  - heartbeat continue after caps
- `scripts/run_true_longrun_8h.sh` contains:
  - both gates
  - `--profile true_longrun_8h`
  - `--min-runtime-minutes 480`
  - `--max-tasks 100`
  - `--max-prs 10`
  - `caffeinate`
- visible heartbeat function/loop emits expected summary text with fake clock/small interval
- backward compatibility:
  - smoke profile unchanged
  - true_longrun_3h/6h unaffected

### 5. Docs

Add/update:
- `docs/117_r7_0_ops_h_true_longrun_8h_heartbeat.md`
- `docs/112_r7_0_ops_longrun_autonomous_runbook.md`
- `docs/01_development_status.md`

Docs must explain:
- why previous 8h attempt stopped at 360m
- `true_longrun_6h` must not be used for 8h runs
- new standard command:
  - `bash scripts/run_true_longrun_8h.sh`
- expected success:
  - `stop_reason=min_runtime reached: 480`
- heartbeat output meaning
- auto-merge remains forbidden

## Tests to run

Run:
- `git diff --check`
- targeted operator/dev_loop tests
- any script/profile tests added

Do not run an actual 8h trial inside this implementation PR.

## PR

Create one PR only.

Do not merge automatically.

## Final report format

Return only one Markdown code block:

```markdown
## State Capsule — R7.0-Ops-H true_longrun_8h + heartbeat

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
