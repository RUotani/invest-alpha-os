# R7.0-Ops-G Cursor Longpack — Make True Long-Run the Standard Autonomous Mode

目的:
R7.0-Ops-F (#70) で追加した native true long-run flags を、実運用で毎回忘れず使えるように **設定・profile・queue・runbook側に標準化**する。

重要:
- このLongpackは「実際に3時間走らせる」ための前準備PRを作る。
- PR作成後、mergeされたら、次の運用runでは `true_longrun_3h` または同等profileで3時間未満では正常終了しない。
- Cursor Agentはこの実装タスク自体を3時間走らせる必要はない。長時間保証は runner 本体・profile・command 側で担保する。

## 前提

- PR #70 `R7.0-Ops-F: Add native true long-run mode` が存在する。
- #70 で以下のflagsが実装済み:
  - `--min-runtime-minutes`
  - `--no-early-success-exit`
  - `--heartbeat-interval-minutes`
  - `--continue-after-pr-limit`
  - `--continue-after-task-limit`
- #70 は merge 後に使う想定。未mergeなら、まず #70 を人間がmergeする。

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

## Required change

Make true long-run operation the standard for autonomous development.

### 1. Add or update a long-run preset/profile

Inspect current profile handling for `overnight_safe_3h`.

Add one of the following, depending on existing architecture:

Preferred:
- profile name: `true_longrun_3h`
- duration: 180 minutes
- min_runtime_minutes: 180
- no_early_success_exit: true
- heartbeat_interval_minutes: 10
- continue_after_pr_limit: heartbeat
- continue_after_task_limit: heartbeat

Optional later profile:
- `true_longrun_6h`
- min_runtime_minutes: 360
- heartbeat_interval_minutes: 10

If profile objects cannot currently carry these fields, add config mapping with minimal code changes.

### 2. Add a one-command operational wrapper

Add a checked-in script or Make target if the repo already uses such pattern.

Preferred new script:
`scripts/run_true_longrun_3h.sh`

Behavior:
- requires `CONFIRM_OPERATOR_DEV_LOOP=YES`
- requires `CONFIRM_GITHUB_PR_CREATE=YES`
- refuses dirty tree except known explicitly allowed local residue if already supported
- uses:
  - `config/tasks/autonomous_dev_queue_longrun.yaml`
  - profile `true_longrun_3h` if implemented, otherwise explicit flags
  - `--execute-dev-loop`
  - `--create-pr`
  - `--wait-ci`
  - `--max-tasks 50`
  - `--max-prs 5`
  - `--min-runtime-minutes 180`
  - `--no-early-success-exit`
  - `--heartbeat-interval-minutes 10`
  - `--continue-after-pr-limit heartbeat`
  - `--continue-after-task-limit heartbeat`
  - `--stop-on-failure`
  - `--stop-on-dirty-tree`

Important:
- This script must NOT merge PRs.
- It may list open PRs at the end.
- It must preserve evidence.

### 3. Add tests

Add tests for:

- profile/preset resolves to min_runtime/no_early_success_exit/heartbeat behavior.
- wrapper command includes the true long-run flags.
- `smoke` queue/profile remains separate and does not default to 3h.
- default behavior remains backward compatible when explicit true long-run profile/flags are not used.

Use fake clock/mocks. Do not run for 180 minutes in tests.

### 4. Update docs

Update or create:

- `docs/114_r7_0_ops_g_true_longrun_standard_profile.md`
- `docs/112_r7_0_ops_longrun_autonomous_runbook.md`
- `docs/01_development_status.md`

Docs must state clearly:

- Cursor Agent finishing a PR implementation in 10 minutes is not itself a long-run trial.
- Real long-run means invoking the runner with `true_longrun_3h` or explicit min-runtime flags.
- `overnight_safe_3h` alone is a max-runtime safety profile, not a minimum-runtime guarantee.
- The new standard command is the script / profile, not ad-hoc manual flags.

### 5. PR

Create one PR only.

Branch:
`work/r7-0-ops-g-true-longrun-standard-profile`

PR title:
`R7.0-Ops-G: Standardize true long-run autonomous profile`

Before PR:
- run targeted tests
- run `git diff --check`
- ensure no generated output/cache/secrets are committed
- no auto-merge

## Final report format

Return only one Markdown code block:

```markdown
## State Capsule — R7.0-Ops-G True Long-Run Standard Profile

| item | value |
|---|---|
| branch | ... |
| start main | ... |
| commit | ... |
| PR | ... |
| CI | ... |

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
