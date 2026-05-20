# Claude Code architecture review template (high-risk)

Use **before** merging or implementing:

- Daily / signals default or footer behavior changes
- Live HTTP or production cache writes
- Portfolio / macro / Veto integration
- New operator bypass of safety gates

## Questions

1. What user-visible behavior changes on the default code path?
2. What fails closed when credentials or env gates are missing?
3. Can tests run without `.env` secrets on CI?
4. What is the rollback story (docs + git revert + cache invalidation)?
5. Does this belong in the same PR or a separate approved phase (e.g. R6.17)?

## Boundaries to verify

- US equities cache read path vs write path
- J-Quants stub vs live client
- Signals report opt-in vs default daily report
- Inventory read-only vs ingest operators

## Output format

```markdown
# Architecture review: <topic>

## Risk level
low / medium / high

## Recommendation
proceed / proceed-with-conditions / block

## Conditions (if any)
1.

## Rollback
- 

## Open questions (max 3)
1.
```

Human approval required for **high** before implementation merge.
