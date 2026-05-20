# Standard clauses (paste into Longpacks)

Agents MUST include or honor these clauses in every Longpack and final report.

## Token-saving mode

- Prefer **minimum human paste / maximum agent autonomy**.
- Use **Longpacks** for multi-step work; avoid many short copy-paste commands for the human.
- **Final report**: single Markdown code block only; no prose outside the block.
- **Never** attach full diff, full file contents, full pytest log, or full CI log.
- Summarize failures by **test name + one-line cause** only.

## Prohibited without explicit approval

- `git push origin main` / main direct push
- `git push --force` / force push
- Branch deletion (`--delete-branch` only when human approves)
- `git worktree remove` / worktree deletion
- Live HTTP (`--live`, vendor APIs) unless Longpack says so and env gates are set
- Cache write (`--write-cache`, population writes) unless explicitly approved
- Changes to `.github/workflows/*`, `Makefile`, `pyproject.toml` unless explicitly approved
- Daily / signals **default** behavior changes unless explicitly approved
- Committing cache JSON under `outputs/` or `.env` / secrets

## Reporting

- Include **State Capsule** in every final report.
- **next actions**: at most **3** items.
- **decisions needed**: list blockers for the human; do not guess high-risk approvals.

## Stop conditions

- Stop after **two consecutive failures** with the same root cause.
- Stop if conflict spreads beyond agreed files (e.g. `docs/01` only for docs PRs).
- Stop if the task requires code changes outside the Longpack scope.
- Stop before merge / force push / live HTTP unless the Longpack explicitly authorizes it.

## Secrets

- Never print `.env` contents, API keys, or `STOOQ_APIKEY` / `JQUANTS_*` values.
- Redact credentials in logs and reports.

## Sound / notification policy

- Do not intentionally play sounds during intermediate steps.
- Keep progress updates text-only.
- At the very end only, if running on macOS and audio is available, play one short completion sound:
  `afplay /System/Library/Sounds/Glass.aiff`
- Never loop sounds.
- If audio fails, ignore and report silently.
