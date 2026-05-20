# R7.0-Ops-G2 Cursor Longpack — Recover True Long-Run Standard Profile after #70 Merge

目的:
#70 `R7.0-Ops-F: Add native true long-run mode` は main に merge 済み。
#71 `R7.0-Ops-G: Standardize true long-run autonomous profile` は #70 を含む stacked PR だったため、#70 merge後に merge conflict になった。
そのため、#71 を無理にmergeせず、main最新から **G差分だけを再適用する recovery PR** を作る。

## 現状

- main includes #70.
- #71 is open but `mergeable=false`.
- `scripts/run_true_longrun_3h.sh` は #71 側の差分なので、まだ main には存在しない。
- そのため `bash scripts/run_true_longrun_3h.sh` は `No such file or directory` になった。
- `docs/smoke.md` は未追跡の試行残骸。コミットしない。必要なら repo 外に退避。

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

## Required approach

Do NOT try to merge #71 directly.
Create a new branch from latest `origin/main`, which already includes #70.

Branch:
`work/r7-0-ops-g2-recover-true-longrun-profile`

PR title:
`R7.0-Ops-G2: Recover true long-run standard profile`

## Implementation intent

Recreate only the G-layer standardization on top of current main:

Required files / changes:
- `config/operator_dev_loop_profiles.yaml`
  - add `true_longrun_3h`
  - add `true_longrun_6h`
  - ensure smoke profile remains non-longrun / backward compatible
- `src/invis_alpha_os/operator/dev_loop.py`
  - use existing #70 long-run flags already in main
  - add minimal profile long-run default resolution only if not already present
  - do not duplicate #70 implementation
- `src/invis_alpha_os/cli/main.py`
  - only add profile/default wiring if needed
  - do not duplicate #70 CLI flags if already in main
- `scripts/run_true_longrun_3h.sh`
  - new executable script
  - requires both gates:
    - `CONFIRM_OPERATOR_DEV_LOOP=YES`
    - `CONFIRM_GITHUB_PR_CREATE=YES`
  - requires clean tree or safely refuses
  - must call `operator-runner dev-loop` with:
    - `--task-queue config/tasks/autonomous_dev_queue_longrun.yaml`
    - `--profile true_longrun_3h`
    - `--execute-dev-loop`
    - `--create-pr`
    - `--wait-ci`
    - `--stop-on-failure`
    - `--stop-on-dirty-tree`
  - if the profile does not fully resolve caps, include explicit:
    - `--max-tasks 50`
    - `--max-prs 5`
    - `--min-runtime-minutes 180`
    - `--no-early-success-exit`
    - `--heartbeat-interval-minutes 10`
    - `--continue-after-pr-limit heartbeat`
    - `--continue-after-task-limit heartbeat`
  - must NOT merge PRs.
- `docs/114_r7_0_ops_g2_recovered_true_longrun_profile.md`
  - explain #71 conflict cause
  - explain #70 already merged
  - explain recovered standard command
- update `docs/112_r7_0_ops_longrun_autonomous_runbook.md`
- update `docs/01_development_status.md`
- tests in `tests/test_operator_dev_loop.py` or a new targeted test file:
  - true_longrun_3h profile resolves min-runtime / no-early-success / heartbeat
  - wrapper script contains required flags/gates
  - smoke profile remains short/non-longrun
  - backward compatibility when flags/profile omitted

## Handling docs/smoke.md

If `docs/smoke.md` exists and is untracked:
- do not commit it
- either ignore it or move it outside repo, e.g. `~/.invest-alpha-os-quarantine/`
- final report should mention it was not committed

## Tests

Run:
- `git diff --check`
- targeted operator tests relevant to dev_loop/profile/script
- do not run actual 180-minute trial in this PR

## PR

Create one PR only against main.
Do not close #71 automatically unless explicitly instructed.
In PR body, mention:
- #71 is superseded by this recovery PR because #70 was merged first.
- #70 already provides native long-run primitives.
- this PR restores G-layer standard profile/script/docs/tests.

## Final report format

Return only one Markdown code block:

```markdown
## State Capsule — R7.0-Ops-G2 Recover True Long-Run Profile

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
