# Return to Main Development v77

Date: 2026-06-02

## Decision

Return from the v74-v76 DCA / averaging-down side line to the main invest-alpha-os development line. The generic
position-aware guard is sufficient for now and should remain a thin observation-only input, not a deeper DCA engine.

## Main Development Order

The next source-only priority order is:

1. weekly report scheduled-run assurance
2. cache-write pilot pre-execution readiness snapshot
3. actual import quarantine follow-through matrix
4. portfolio strategy observation report integration
5. ChatGPT main-development handoff summary

## Rationale

v76 removed JFE/Honda special casing and generalized the position-aware guard for arbitrary symbols. Continuing to deepen
that feature would risk turning a side support tool into a dedicated nanpin engine. The higher-value path is to restore
focus to scheduled weekly reporting, cache-write readiness, actual-import separation, and portfolio strategy reporting.

## Source-Only Boundary

v77 is a report/CLI/context-pack milestone only. It consolidates and summarizes already established gates without
executing any operational step.

## Explicit Non-Approval

- provider live access: not approved
- live HTTP: not approved
- cache write: not approved
- cache directory creation: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- broker API access: not approved
- raw broker export parsing: not approved
- raw OHLCV/API persistence: not approved
- env secret display: not approved
- workflow direct change: not approved
- dependency / pyproject change: not approved
- trading action or order placement: not approved

## Next Decision Point

Observe the next weekly candidate brief scheduled run first. Separately decide later whether a scoped cache-write pilot
approval phrase should be issued. Actual import remains quarantined until a future cache-write pilot result review and
separate actual-import approval package exist.
