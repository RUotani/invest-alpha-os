# Safety rules (invest-alpha-os)

## Explicit approval required

| Action | Gate |
|---|---|
| Live HTTP | Longpack + `CONFIRM_*=YES` env vars as documented |
| US cache write | `CONFIRM_US_CACHE_WRITE=YES` + operator runbook |
| Workflow / Makefile / `pyproject.toml` | Human approval in Longpack |
| Daily / signals default change | Human + **Claude Code** architecture review |
| Portfolio / macro / Veto wiring | Human + architecture review |
| Merge to `main` | PR + green required check (`test`) |
| Force push | Human only; never on `main` |

## Always forbidden

- Push directly to `main`
- Force push (especially `main`)
- Delete branches or worktrees unless human requests
- Print or commit secrets / `.env`
- Commit `outputs/market_data/**` cache JSON
- `rm -rf` on repo paths (use project scripts conventions)

## Worktrees

- Many historical worktrees exist; **do not remove** unless instructed.
- **Do not touch** operator-marked worktrees (e.g. `invest-alpha-os-r6-10-g`) without explicit approval.
- Prefer dedicated worktree for `main` updates when the primary checkout is on a feature branch.

## CI vs local

- Local `make main-gate` may fail when `.env` exports `JQUANTS_*`; prefer **GitHub Actions** for merge decisions when docs-only.
- Unset `JQUANTS_*` for isolated pytest when validating golden tests locally.

## High-risk review

Before live HTTP, cache write, or default behavior changes, run **Claude Code** review using `.agent/claude_arch_review_template.md`.
