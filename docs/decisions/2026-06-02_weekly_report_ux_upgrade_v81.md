# Weekly Report UX Upgrade v81

Date: 2026-06-02

## Decision

Upgrade Weekly Candidate Brief from a generation confirmation artifact into a more readable investment decision support
report while keeping it observation-only and source-only.

The v81 upgrade adds:

- no-candidate summary
- portfolio constraint block using the v78 redacted 2026-05 month-end context
- action classification scaffold
- Do / Don't checklist
- ChatGPT review prompt context
- improved no-candidate email/mobile preview wording

## Rationale

v80 reviewed the v79 artifact and found that the workflow and artifact path worked, but a zero-candidate report looked
empty and did not explain why no candidate was selected, what should not be done, or how the weekly report should connect
to the user's portfolio constraints.

The user's redacted 2026-05 month-end context shows:

- cash: 508.2万円 / 11.7%
- equity total: 2,934.5万円 / 67.8%
- individual stocks: 846.3万円 / 19.6%

Given cash is below the 15% minimum guide and individual stocks are above the desired 10-15% direction, the weekly report
should avoid encouraging unnecessary new risk when candidates are weak or data-blocked.

## Scope

v81 is a rendering and UX upgrade only. It does not change the scheduler, data fetchers, cache behavior, actual import
behavior, broker handling, or trading behavior.

## Explicit Non-Approval

- provider live HTTP: not approved
- market-data live fetch: not approved
- cache write: not approved
- cache directory creation: not approved
- actual refresh/import: not approved
- manual actual import: not approved
- broker API access: not approved
- raw broker export parsing: not approved
- env/secret display: not approved
- workflow direct change: not approved
- dependency / pyproject change: not approved
- trading action / order placement: not approved

## Next Decision Point

After v81, the next likely source-only milestone is a portfolio-aware weekly action checklist or cleanup priority scoring
pack, depending on whether the user wants weekly action control or cleanup ranking first.
