# Next 24h Development Tree Proposal

Version: 2026-06-05

## Purpose

This proposal keeps the next 24 hours focused on weekly scheduled-run assurance, report artifact quality, and
operator-facing clarity without crossing any hard gate.

## Hard Gates

The next 24 hours remain source-only, fixture-only, docs-only, stdout-only, or read-only depending on the task.

Do not execute:

- workflow change or `.github/workflows` edit
- manual workflow_dispatch or rerun
- live HTTP / market-data live fetch
- cache write or cache directory creation
- actual refresh/import or manual import
- broker API, broker login, raw broker export parsing
- raw Excel direct parsing
- env/secret display
- dependency / pyproject / Makefile change
- trading action, order placement, automated trading
- real email send

## Time-Gated Observation

Natural scheduled run observation is only meaningful after 2026-06-06 07:30 JST.

| Time Window | Classification | Allowed Action |
| --- | --- | --- |
| Before 2026-06-06 07:30 JST | `NOT_YET_OBSERVABLE` | record wait state only |
| After 2026-06-06 07:30 JST and `event=schedule` exists | `OBSERVABLE` | inspect run metadata read-only |
| After 2026-06-06 07:30 JST and no `event=schedule` exists | `OBSERVABILITY_MISS` | classify trigger/scheduler gap |

Manual dispatch, rerun, or workflow edits are not allowed for this observation.

## Primary Branches

| Branch | Entry Condition | Output | Stop Condition |
| --- | --- | --- | --- |
| Scheduled run success | schedule run exists and succeeds | read-only observation report plus artifact verification status | artifact schema mismatch or missing required preview files |
| Scheduled run failure | schedule run exists and fails/cancels | failure classification report | log inspection would require secret display or rerun |
| Scheduled run miss | no schedule event after target time | trigger/observability miss report | workflow edit is required |
| Artifact partial | run succeeds but artifact set is incomplete | local verification findings | raw data would need to be downloaded or committed |
| Artifact success | report/copy/email/status artifacts satisfy contract | scheduled-run assurance snapshot | none |

## Recommended PR Order

1. Scheduled natural run observation report after the target time.
2. Weekly artifact/status verification hardening only if the observation exposes a schema gap.
3. Monthly review pack follow-up only if monthly integration starts drifting from v84/v95/v109 contracts.
4. Raw input quarantine design review only as docs/source-only work.
5. STATE.md refresh only if a checker proves the exact safe delta and the queue needs a new SSoT snapshot.

## Decision Rules

- If the natural scheduled run is not yet observable, do not fabricate confidence from manual runs.
- If the scheduled run is missing, classify it as scheduler/observability work before looking for report content bugs.
- If the scheduled run succeeds but artifacts are incomplete, keep the issue in artifact generation/export scope.
- If artifacts are complete, treat the weekly scheduled-report path as observed and move to UX/content quality follow-up.
- If a proposed fix requires workflow change, stop at a copy-ready patch proposal and request human approval.

## Next 24h Output Shape

Each completed branch should produce:

- a concise decision or review artifact under `docs/decisions/` or `docs/reviews/`
- focused tests for marker coverage or renderer contracts when source/docs change
- a small PR with CI green and mergeable CLEAN before squash merge
- a final status line suitable for the operator dashboard and ChatGPT handoff

## ChatGPT Handoff Summary

The next agent should first check whether 2026-06-06 07:30 JST has passed. If not, keep scheduled-run observation as
`NOT_YET_OBSERVABLE` and work only on source-only hardening. If yes, inspect GitHub Actions run metadata read-only for
`weekly_candidate_brief.yml` and classify schedule success, failure, or miss before touching any report artifact.
