# Cursor Agent Longpack template

## purpose

One paste for the human; the agent executes end-to-end with minimal follow-up.

## current state

- `origin/main` commit:
- Open PRs / branches:
- Working tree / worktrees:
- What is already merged vs in-flight:

## allowed scope

- List files or areas the agent may change.
- List commands (e.g. `pytest` paths, `gh pr create`).

## prohibited actions

- Copy from `.agent/standard_clauses.md` and `.agent/safety_rules.md`.
- Add task-specific prohibitions (e.g. no R6.17 implementation).

## autonomous rules

- Low-risk docs/tests: proceed without asking.
- Resolve `docs/01` conflicts when scope is docs-only.
- Stop if conflicts leave allowed files or CI fails twice for the same reason.
- Final report: `.agent/report_template.md` (single code block).

## stages

1. State confirmation
2. Implementation / merge / PR
3. CI watch
4. Post-merge verification (if authorized)
5. Final report

## final report format

- Single Markdown code block only.
- Include State Capsule, changed files, tests, CI, safety, failures, decisions needed, next actions (max 3).
