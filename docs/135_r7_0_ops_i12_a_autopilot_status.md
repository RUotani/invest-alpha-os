# R7.0-Ops-I12-A — Operator autopilot status

**Goal**: One command for Cursor Agent / operator — no copy-paste of `git status`, `gh pr list`, main CI, latest longrun evidence.

## Command

```bash
.venv/bin/python -m invis_alpha_os.cli.main operator-runner autopilot-status
.venv/bin/python -m invis_alpha_os.cli.main operator-runner autopilot-status --format json
.venv/bin/python -m invis_alpha_os.cli.main operator-runner autopilot-status --run-id 20260523T112747Z
```

## Includes

- `origin/main` SHA (optional `git fetch` — network/git metadata read only; use `--no-fetch` offline)
- working tree clean / dirty count
- open PR summary (read-only `gh pr list`)
- latest main CI run (`gh run list --branch main`)
- latest dev-loop evidence (tasks, PRs, stop_reason, suggested `post-run-review` / `post-run-integrate` commands)

## Does not

- merge PRs
- push to main
- live HTTP / cache / Gmail
- print `.env` or secret-like paths in status (dirty count still reflects redacted paths; see `dirty_paths_redacted`)

## Human retains

Merge approval, high-risk gates, `--execute --integrate`, starting longruns.
