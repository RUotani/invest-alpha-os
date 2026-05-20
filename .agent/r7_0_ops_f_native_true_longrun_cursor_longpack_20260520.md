# R7.0-Ops-F Cursor Longpack — Native True Long-Run Mode

目的: `operator-runner dev-loop` を、外部shell supervisorではなく **runner本体で長時間継続できる設計** に変更する。

背景:
- これまでの早期終了原因は、`1 task / 1 PR / CI check / completion report` 型の制御だった。
- 直近のTerminal supervisorでは、`dev-loop` が `tasks=3/6 prs=3` まで進んだ後、`stop_reason=max_prs reached: 3` で停止した。
- 外側scriptが `dev_loop_rc=1` を failure と扱ったため止まったが、これは実質的には「上限到達」であり、致命的エラーではない。
- 今後は `max_prs reached` / `max_tasks reached` を即終了理由にせず、`min-runtime` 到達まで heartbeat / wait / next-cycle を継続できる native mode を実装する。

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

Implement native true long-run controls in `operator-runner dev-loop`.

### New CLI options

Add the following options:

```bash
--min-runtime-minutes <int>
--no-early-success-exit
--heartbeat-interval-minutes <int>
--continue-after-pr-limit <wait|heartbeat|next-cycle|stop>
--continue-after-task-limit <wait|heartbeat|next-cycle|stop>
```

Recommended defaults:
- default behavior must remain backward compatible.
- `--no-early-success-exit` is opt-in only.
- if `--min-runtime-minutes` is omitted, current behavior should remain unchanged.
- if `--continue-after-pr-limit` is omitted, current behavior should remain unchanged.
- if `--continue-after-task-limit` is omitted, current behavior should remain unchanged.

### Required behavior

When `--min-runtime-minutes 180 --no-early-success-exit` is set:

1. The run must not return successful completion before 180 minutes have elapsed.
2. `max_prs reached` is not a fatal error.
3. `max_tasks reached` is not a fatal error.
4. If PR cap is reached before min-runtime:
   - record evidence
   - wait or heartbeat until either:
     - min-runtime is reached, or
     - a real failure occurs
5. If task queue is exhausted before min-runtime:
   - record evidence
   - heartbeat until min-runtime is reached
6. If dirty tree, failed tests, failed CI, rejected safety validator, or unexpected exception occurs:
   - stop immediately with non-zero exit
   - record evidence
7. Evidence must clearly distinguish:
   - `failure`
   - `controlled_stop`
   - `cap_reached_waiting`
   - `heartbeat_waiting`
   - `min_runtime_reached`
8. The final `stop_reason` for successful long-run should be:
   - `min_runtime reached: <minutes>`
   not:
   - `max_prs reached`
   - `max_tasks reached`

### Return code contract

Fix or document return code semantics.

Expected:
- real failure: non-zero
- successful min-runtime completion: zero
- cap reached while `--no-early-success-exit` and min-runtime not reached: do not exit; continue heartbeat/wait
- cap reached without long-run options: preserve current behavior

### Evidence requirements

Update evidence JSON to include:

```json
{
  "min_runtime_minutes": 180,
  "elapsed_minutes": 0,
  "no_early_success_exit": true,
  "heartbeat_interval_minutes": 10,
  "continue_after_pr_limit": "heartbeat",
  "continue_after_task_limit": "heartbeat",
  "longrun_state": "heartbeat_waiting",
  "cap_reached": {
    "tasks": true,
    "prs": true
  }
}
```

Do not commit generated evidence output.

## Tests required

Add tests covering:

1. Backward compatibility:
   - existing smoke behavior unchanged when new flags are omitted.

2. PR cap reached under long-run:
   - does not terminate as failure.
   - enters heartbeat/wait state.
   - evidence includes cap_reached and longrun_state.

3. Task cap reached under long-run:
   - does not terminate as failure.
   - enters heartbeat/wait state.

4. Min-runtime reached:
   - exits zero.
   - final stop_reason is `min_runtime reached`.

5. Real failure still stops:
   - dirty tree / failed CI / failed task still exits non-zero even under long-run mode.

Use mocks/fake clock so tests do not actually wait 180 minutes.

## Docs required

Update or create docs:

- `docs/113_r7_0_ops_f_native_true_longrun_mode.md`
- `docs/01_development_status.md`
- optionally update `docs/112_r7_0_ops_longrun_autonomous_runbook.md`

Docs must clearly state:

- `overnight_safe_3h` is a maximum runtime profile, not a guarantee by itself.
- true long-run requires:
  - `--min-runtime-minutes`
  - `--no-early-success-exit`
  - heartbeat/wait behavior after caps.
- `--max-tasks 1 --max-prs 1` is smoke-only.
- long-run standard should use larger caps, e.g.:
  - `--max-tasks 50`
  - `--max-prs 5`
  - `--min-runtime-minutes 180`
  - `--no-early-success-exit`
  - `--heartbeat-interval-minutes 10`
  - `--continue-after-pr-limit heartbeat`
  - `--continue-after-task-limit heartbeat`

## Suggested future command after merge

Do not run this for 3 hours inside this implementation task unless explicitly requested later.
Add it to docs as the post-merge operational command.

```bash
CONFIRM_OPERATOR_DEV_LOOP=YES \
CONFIRM_GITHUB_PR_CREATE=YES \
.venv/bin/python -m invis_alpha_os.cli.main operator-runner dev-loop \
  --task-queue config/tasks/autonomous_dev_queue_longrun.yaml \
  --profile overnight_safe_3h \
  --execute-dev-loop \
  --create-pr \
  --wait-ci \
  --max-tasks 50 \
  --max-prs 5 \
  --min-runtime-minutes 180 \
  --no-early-success-exit \
  --heartbeat-interval-minutes 10 \
  --continue-after-pr-limit heartbeat \
  --continue-after-task-limit heartbeat \
  --stop-on-failure \
  --stop-on-dirty-tree
```

## PR requirements

Create one PR only.

Branch name:
`work/r7-0-ops-f-native-true-longrun-mode`

PR title:
`R7.0-Ops-F: Add native true long-run mode`

Before PR:
- run targeted tests
- run `git diff --check`
- ensure no generated output/cache/secrets are committed
- ensure no workflow/Makefile/pyproject changes unless strictly necessary

## Final report format

Return only one Markdown code block containing:

```markdown
## State Capsule — R7.0-Ops-F Native True Long-Run Mode

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
