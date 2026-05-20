# Claude Code — R6.17 architecture review prompt (pre-implementation)

**Do not implement.** High-risk design review only.

## Purpose

Confirm architecture boundaries before R6.17 implementation Longpack runs.

## Artifacts to read

- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](../docs/65_r6_17_opt_in_us_cache_preview_plan.md) (§5 locked policies)
- [.agent/r6_17_cursor_longpack_draft.md](./r6_17_cursor_longpack_draft.md)
- [docs/66_r6_17_pre_implementation_review_pack.md](../docs/66_r6_17_pre_implementation_review_pack.md)

## Boundary questions

### Layers

- **data**: read-only cache / inventory only
- **metrics**: derived fields (`return_*`, `volume_status`) — reuse vs new
- **signals**: preview must **not** feed scoring when stale
- **cli**: opt-in flag only; default path unchanged
- **docs/tests**: opt-in golden only

### Contracts

- Output columns per docs/65 §5.4
- Freshness gate per R6.16-E inventory status
- Stale policy §5.1 (mark + warn; no silent valid input)

### Defaults

- Daily report default section: **unchanged**
- US signals default: **unchanged**

### Future risk

- Veto / portfolio / macro hooks must not appear in R6.17 PR
- Production hard gate (SPY/QQQ fresh_enough) is **future**, not R6.17 v1

### Safety

- No live HTTP · no cache write · no trading recommendation
- Rollback: flag off restores current behavior

### Testing

- CI without `.env` secrets
- Default-path regression suite unchanged

## Merge readiness (for later implementation PR)

Block merge if:

- Default path behavior changes without approval
- Stale rows used for scoring
- New required env vars for default daily run
- Workflow/Makefile/pyproject changed without approval

## Output format

Use `.agent/claude_arch_review_template.md` structure:

- Risk level: expect **medium** for R6.17 v1 (opt-in only)
- Recommendation: proceed-with-conditions / block
- Conditions and rollback required
