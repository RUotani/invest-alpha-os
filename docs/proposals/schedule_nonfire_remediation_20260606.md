# Schedule Non-Fire RCA and Delivery Expectation Hardening — 2026-06-06

## Summary

The 2026-06-06 weekly candidate brief remained usable through the local/manual issue pack, but the natural GitHub
Actions schedule was not observed. This is a scheduled automation evidence gap, not proof that the v1.0 report
generation core failed.

## Observed Fact

- `weekly_candidate_brief.yml` had no visible `event=schedule` run after the expected 2026-06-06 07:00 JST window.
- The recent visible workflow runs were `workflow_dispatch` runs.
- `workflow_dispatch` was not executed as part of this RCA.
- The 2026-06-06 weekly report was generated locally and is user-readable from
  `reports-private/manual_issue/weekly_20260606/README_FOR_USER.md`.
- Gmail was not sent.

## Impact

- A natural scheduled artifact was not produced or verified.
- The scheduled automation path remains pending.
- Gmail non-arrival is expected under current v1.0 boundaries because real email sending is NO-GO.
- v1.0 first-use remains usable through local Markdown reports and email preview artifacts.

## User-Facing Interpretation

- `v1_usable_tomorrow: true` can remain valid when `schedule_status: pending`.
- The canonical v1.0 delivery path is local Markdown or artifact preview, not a Gmail inbox.
- Missing Gmail is not automatically a report-generation failure.
- Manual issue packs should be read before treating the scheduled automation gap as a user-facing report gap.

## Possible Causes To Investigate

| Cause | Why It Matters | Safe Check |
| --- | --- | --- |
| workflow schedule state | schedule may be disabled or inactive | read-only workflow metadata inspection |
| cron definition or timezone mismatch | UTC/JST conversion may be misunderstood | compare `0 22 * * 5` with Saturday 07:00 JST |
| workflow disabled/inactive state | GitHub can disable workflows after inactivity or settings changes | read-only repository Actions settings review by a human |
| GitHub scheduler delay/non-fire | scheduled workflows are not guaranteed to start exactly on time | repeat read-only observation on the next expected window |
| workflow file not present on default branch | schedule only runs from default branch | compare default branch history at the expected time |
| repository Actions settings | org/repo settings can block schedules | human settings review; do not infer from source only |

## Safe Remediation Options

1. Repeat read-only natural scheduled observation on the next expected Saturday window.
2. Keep using the local/manual weekly report pack as the v1.0 fallback.
3. Prepare proposal-only workflow improvements for artifact upload or schedule diagnostics.
4. Add status wording that distinguishes `schedule_status: pending`, `delivery_mode: local_markdown_or_artifact_preview`,
   and `gmail_sent: false`.

## Explicit Non-Options

- Do not use `workflow_dispatch` as proof of schedule success.
- Do not add real Gmail sending now.
- Do not change `.github/workflows/*` without explicit human approval.
- Do not use live HTTP, market-data fetch, cache write, actual import, broker API, raw Excel parsing, env/secret display,
  trading action, or real email send.

## Proposed Status Contract

| Field | Current Value | Meaning |
| --- | --- | --- |
| `schedule_status` | `pending` | natural schedule is not yet proven |
| `delivery_mode` | `local_markdown_or_artifact_preview` | canonical v1.0 delivery is local/manual output or preview artifact |
| `gmail_sent` | `false` | real email sending remains out of scope |
| `v1_usable_tomorrow` | `true` | core report review can proceed even while schedule proof is pending |

## Next Action

Observe the next natural scheduled run read-only. If no `event=schedule` appears again after the expected window,
classify the issue as a scheduler/observability gap and prepare a human-approved workflow remediation proposal.
