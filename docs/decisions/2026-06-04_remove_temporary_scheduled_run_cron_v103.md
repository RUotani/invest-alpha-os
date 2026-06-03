# Remove Temporary Scheduled Run Cron v103

Date: 2026-06-04

## Decision

Remove the temporary v102 scheduled trigger `0 22 3 6 *` from `.github/workflows/weekly_candidate_brief.yml` and keep the
normal weekly schedule `0 22 * * 5`.

## v86 Observation Result

Observation window:

- target schedule: 2026-06-04 07:00 JST
- observation checks: 2026-06-04 07:36 JST and 2026-06-04 07:48 JST
- workflow: `weekly_candidate_brief.yml`
- expected event: `schedule`
- result: `scheduled run not observed`

The workflow was active and the temporary cron was present on `main`, but `gh run list` for `weekly_candidate_brief.yml`
showed only earlier `workflow_dispatch` runs. A broader repository run list also did not show a matching scheduled run
near 2026-06-04 07:00 JST.

Because no matching scheduled run was observed, no actual scheduled artifact set was downloaded or inspected. The
pre-v86 manual-reference run had already shown that weekly report, copy report, and email preview txt/html can be
generated, while Gmail non-delivery remains expected because real email send is not enabled.

## Revert Rationale

GitHub Actions cron does not support a year field. Leaving `0 22 3 6 *` in place would create an annual June 4 trigger
that is no longer useful after the v86 observation window. The normal weekly Saturday schedule remains the source of
truth for future scheduled weekly candidate brief runs.

## Safety Boundary

- manual workflow_dispatch: not executed
- provider live HTTP or market-data live fetch: not executed
- cache write: not executed
- actual import: not executed
- broker API or raw Excel direct parsing: not executed
- raw broker/OHLCV/API persistence: not executed
- env/secret display: not executed
- dependency / pyproject / Makefile change: not changed
- trading action or real email: not executed

## Next Decision Point

Treat v86 as a schedule-trigger observation miss rather than an artifact quality failure. Next follow-up should harden
scheduled-run observability without manual dispatch, for example by improving artifact schema/status expectations and
adding a versionless observation facade.
