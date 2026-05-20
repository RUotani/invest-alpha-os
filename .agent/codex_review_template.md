# Codex PR review template (read-only)

## Scope

- **Read-only** first: no commits unless the human promotes to fix PR.
- Use GitHub connector / `gh pr view` / `gh pr diff` (summarize, do not paste full diff).

## Checklist

1. **Contract break**: public CLI flags, JSON shapes, report footers.
2. **Tests**: new behavior covered; no env-dependent assertions without isolation.
3. **Architecture boundary**: US cache vs daily/signals vs J-Quants; no accidental default changes.
4. **Safety**: live HTTP, cache write, secrets, workflow/Makefile/pyproject untouched unless claimed.
5. **Docs**: `docs/01` timeline consistent; links valid.

## Output format (concise)

```markdown
# Codex review: PR #<n>

## Verdict
approve / request-changes / comment-only

## Findings (max 5 bullets)
- 

## Tests gap
- none / ...

## Safety
- 

## Suggested follow-ups (max 3)
1.
```

No full file dumps; cite paths and line ranges sparingly.
