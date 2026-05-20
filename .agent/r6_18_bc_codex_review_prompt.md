# Codex — R6.18-B+C planning review prompt (read-only)

**Do not implement.** Review docs/templates-only planning PR.

## Purpose

Read-only audit of R6.18-B+C cache-only connection planning before any B1 product code PR:

- [docs/74_r6_18_bc_cache_only_connection_design.md](../docs/74_r6_18_bc_cache_only_connection_design.md)
- [docs/75_r6_18_bc_default_enablement_readiness_checklist.md](../docs/75_r6_18_bc_default_enablement_readiness_checklist.md)
- [docs/76_r6_18_bc_implementation_review_pack.md](../docs/76_r6_18_bc_implementation_review_pack.md)
- [.agent/r6_18_bc_implementation_longpack_draft.md](./r6_18_bc_implementation_longpack_draft.md)
- [docs/01_development_status.md](../docs/01_development_status.md) — R6.18-B+C section only

## Recommended settings

- **Read-only** · no commits unless human promotes to fix PR
- Auto-review **OFF** or low
- **No full logs** in output

## Review checklist

1. **B+C scope consistency**: B = connection design; C = default readiness; no hidden implementation in planning PR
2. **No default enablement**: docs/75 states blocked; no PR text implying default on
3. **B1 recommendation only**: B2/B3 rejected or deferred; B1 is sole implementation candidate
4. **No hidden product code**: planning PR is docs/templates only
5. **No workflow/Makefile/pyproject** changes in planning scope
6. **No buy/sell/recommendation language** in output contracts
7. **Checklist completeness**: preconditions, decision matrix, rollback, evidence table
8. **Implementation Longpack safety**: DO NOT EXECUTE banner; forbidden live HTTP/cache write/default enable
9. **Architecture boundaries**: metrics / preview / CLI separation; no Veto/portfolio/macro
10. **R6.17-D premise**: stale 0 used as planning state; no stale refresh in planning PR

## Verdict options

- `APPROVED_FOR_R6_18_B1_IMPLEMENTATION_DRAFT`
- `APPROVED_WITH_MINOR_NOTES`
- `BLOCKED_REVISE_PLANNING`

## Output format

Final report: **one Markdown code block**.

```markdown
# Codex R6.18-B+C planning review

## Verdict
APPROVED_FOR_R6_18_B1_IMPLEMENTATION_DRAFT | APPROVED_WITH_MINOR_NOTES | BLOCKED_REVISE_PLANNING

## Findings (max 5)
-

## Checklist gaps
-

## Safety
-

## Before B1 implementation (max 3)
1.
```
