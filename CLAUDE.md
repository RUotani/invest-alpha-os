# Claude Code — invest-alpha-os

## Project purpose

Investment research / signals tooling with strict safety gates: US equities cache (read-first), optional J-Quants, daily report and signals boundaries. See `docs/10_system_overview_for_external_review.md` and `docs/01_development_status.md`.

## Agent workflow policy

- **Minimum human paste, maximum agent autonomy** for multi-step work.
- Longpacks live under `.agent/`; final reports use `.agent/report_template.md`.
- Standard prohibitions: `.agent/standard_clauses.md` and `.agent/safety_rules.md`.

## Risk levels

| Level | Examples | Review |
|---|---|---|
| Low | Docs, templates, read-only inventory smoke | Cursor Agent self-serve |
| Medium | CLI additions, inventory fields, preview commands | Cursor + Codex PR review |
| High | Live HTTP, cache write, daily/signals defaults, Veto/portfolio/macro | **Claude Code** arch review required |

## Safety rules (summary)

- No push to `main`; use PRs only.
- No force push; no branch/worktree deletion unless human asks.
- No secrets or `.env` in output or commits.
- Live HTTP and cache write only with explicit Longpack approval and env gates.
- Do not change workflow / Makefile / `pyproject.toml` without explicit approval.
- Do not change daily/signals **defaults** without explicit approval.

## Reporting

- Return **one** Markdown code block; no prose outside it.
- No full diffs, full files, or full test/CI logs.
- Include State Capsule; at most 3 next actions.

## Worktrees

- Dozens of registered worktrees may exist; **do not remove** unless instructed.
- **Do not modify** `invest-alpha-os-r6-10-g` without explicit operator approval.

## Detail doc

R6.16-F: `docs/64_r6_16_f_agent_workflow_standardization.md`
