# Temporary Scheduled Run Advance v102

Date: 2026-06-03

## Decision

Temporarily add an extra scheduled trigger to the weekly candidate brief workflow so the v86 scheduled run observation
can be performed on 2026-06-04 instead of waiting until 2026-06-06.

## Rationale

The normal weekly candidate brief schedule remains `0 22 * * 5` UTC, which corresponds to Saturday 07:00 JST. The next
normal observation window was 2026-06-06 07:30 JST or later. For this PR only, the user explicitly approved the minimum
`.github/workflows` schedule change needed to create an earlier natural scheduled run.

The added temporary trigger is:

```yaml
- cron: "0 22 3 6 *"
```

This corresponds to 2026-06-03 22:00 UTC, or 2026-06-04 07:00 JST. Because GitHub Actions cron does not support a year
field, this trigger must be removed after the v86 scheduled run observation completes.

## Scope

- Keep the normal weekly schedule unchanged.
- Add one temporary early observation schedule line.
- Preserve `workflow_dispatch` availability but do not manually dispatch the workflow.
- Prepare the v86 observation window for 2026-06-04 07:30 JST or later.

## Observation Targets

Use the v101 checklist against the actual scheduled artifact set:

- workflow run trigger is `schedule`
- run conclusion is `success`
- `weekly_candidate_brief_v0_1.md`
- `weekly_candidate_brief_copy.md`
- `weekly_candidate_brief.json`
- `email/email_preview.txt`
- `email/email_preview.html`
- `status.json`
- Score / Veto markers
- Pipeline markers
- Sanitized / Manual Input markers
- User-Facing Input Review markers
- cash 11.7%
- individual stocks 19.6%
- non-trading safety wording

## Explicit Non-Approval

- manual workflow_dispatch: not approved / not executed
- provider live HTTP or market-data live fetch: not approved / not executed
- cache write: not approved / not executed
- actual refresh/import or manual actual import: not approved / not executed
- broker API, broker login, or raw broker export parsing: not approved / not executed
- raw broker data, raw OHLCV/API, or raw Excel direct parsing: not approved / not executed
- reports-private raw data write or git-tracked raw data write: not approved / not executed
- env/secret display: not approved / not executed
- dependency / pyproject / Makefile change: not approved / not changed
- trading action, order placement, auto-trading, or real email: not approved / not executed

## Revert Requirement

After the 2026-06-04 scheduled observation completes, create a follow-up PR that removes only the temporary
`0 22 3 6 *` cron line and its comment. Do not remove the normal `0 22 * * 5` weekly schedule.
