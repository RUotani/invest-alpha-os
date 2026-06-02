# v94 Weekly Report Trial Review / UI QA

Date: 2026-06-02

## Scope

Review the merged v93 weekly report draft using source-only / fixture-only artifacts. The review focused on:

- weekly report section order and readability
- `Score / Veto` integration summary readability
- email preview txt/html compact summary
- Markdown / JSON / email consistency
- safety wording that prevents score/veto output from looking like an execution prompt

## Trial Artifact Boundary

Artifacts were generated under `/private/tmp/invest-alpha-os-v94-weekly-report-trial-20260602`.

The final reviewed artifacts are fixture-only. No workflow dispatch, provider live HTTP, market-data live fetch,
cache write, actual import, broker API, raw broker export parsing, env/secret display, order placement, or real email
send was executed.

## Findings

| Finding | Severity | Result |
|---|---|---|
| `Score / Veto` summary had no blank line before the next section in copy-ready Markdown | SHOULD_FIX | Fixed by preserving a trailing blank line after the rendered section |
| Long multi-veto cell for `HYPE_E` made the table hard to scan | SHOULD_FIX | Fixed by compressing veto keys after the first two keys, e.g. `+6` |
| Email preview correctly used compact summary instead of the full table | PASS | No change |
| JSON and Markdown carried the same score band / pipeline classification | PASS | Added v94 consistency test |
| `HIGH_CONVICTION_REVIEW` can still sound strong to humans | WATCH | Kept as v91 contract wording; safety lines remain explicit that it is not an execution instruction |

## QA Result

The v94 reviewed draft is readable enough for scheduled artifact review after the two UI fixes above.

Remaining risk is wording-level: `HIGH_CONVICTION_REVIEW` is intentionally part of the v91 contract, but future report
iterations may consider a more neutral display label if human review finds it too strong.

## Safety Boundary

This review is source-only and fixture-only. It does not approve:

- workflow changes
- manual workflow dispatch
- provider live HTTP
- market-data live fetch
- cache write
- actual refresh/import
- broker API
- raw data persistence
- env/secret display
- dependency / pyproject / Makefile changes
- trading action or order placement
- real email send
