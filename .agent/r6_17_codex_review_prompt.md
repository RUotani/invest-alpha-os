# Codex — R6.17 pre-implementation review prompt (read-only)

**Do not implement.** Review planning artifacts only.

## Purpose

Read-only audit of R6.17 planning before any product code PR:

- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](../docs/65_r6_17_opt_in_us_cache_preview_plan.md)
- [.agent/r6_17_cursor_longpack_draft.md](./r6_17_cursor_longpack_draft.md)
- [docs/66_r6_17_pre_implementation_review_pack.md](../docs/66_r6_17_pre_implementation_review_pack.md)

## Recommended settings

- **Read-only** · no commits unless human promotes to fix PR
- Auto-review **OFF** or low
- Intelligence **medium/high** (cost vs depth tradeoff)
- **No full logs** in output

## Review checklist

1. **Scope**: docs/65 allowed vs prohibited scope is coherent
2. **Longpack draft**: `.agent/r6_17_cursor_longpack_draft.md` prohibitions complete; no accidental merge instruction
3. **Stale handling**: marked in preview; not used for scoring; warnings required
4. **Benchmarks**: SPY/QQQ core; TLT/GLDM reference; stale does not block initial preview
5. **Output columns**: allowed list only; no buy/sell / Veto / macro final judgment
6. **Tests**: opt-in-only golden; env-independent; default golden untouched
7. **Defaults**: daily/signals default enable explicitly forbidden
8. **Safety**: live HTTP / cache write forbidden
9. **Gaps**: missing contracts before implementation PR

## Output format

```markdown
# Codex R6.17 planning review

## Verdict
approve / request-changes / comment-only

## Findings (max 5)
-

## Test plan gaps
-

## Safety
-

## Before implementation Longpack (max 3)
1.
```

Use `.agent/codex_review_template.md` for PR-phase reviews after code exists.
