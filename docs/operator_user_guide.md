# Operator / User Guide — Weekly and Monthly Report Surface

Version: 2026-06-05

## 3-Line Summary

- This guide is the safe entry point for weekly/monthly report review, artifact verification, and operator summaries.
- All commands here are source-only, fixture-only, stdout-only, or read-only unless explicitly stated otherwise.
- Workflow change, manual workflow_dispatch, live HTTP, cache write, actual import, broker/raw input handling, secret display, trading action, and real email send remain forbidden.

## What This Guide Covers

- weekly scheduled run observation
- weekly artifact and `status.json` verification
- monthly review pack integration check
- report UX language contract
- operator dashboard and progress/STATE consistency checks
- sample output regeneration contract

## Safe Command Index

| Purpose | Command | Mode |
| --- | --- | --- |
| v1.0 operational readiness | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main v1-readiness-check --format markdown` | read-only |
| Weekly artifact/status verification | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main weekly-artifact-local-verify --report-date 2026-06-06` | local read-only verification |
| Operator dashboard summary | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main operator-dashboard-summary --format markdown` | stdout-only |
| Progress dashboard consistency | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main progress-dashboard-check --format markdown` | read-only |
| STATE.md consistency | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main state-consistency-check --format markdown` | read-only |
| Sample regeneration contract | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main sample-output-regeneration-contract --format markdown` | contract output only |
| Monthly review integration | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main monthly-review-pack-integration --format markdown` | fixture-only |
| Report UX language contract | `env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main report-ux-language-contract --format markdown` | contract output only |

## Weekly Scheduled Run Observation

Natural scheduled run observation is read-only.

Use after the expected observation time:

```bash
gh run list --repo RUotani/invest-alpha-os --workflow weekly_candidate_brief.yml --limit 10 --json databaseId,displayTitle,event,headSha,status,conclusion,createdAt,updatedAt,url
```

Classify the result before inspecting artifacts:

| Observation | Classification | Next Step |
| --- | --- | --- |
| `event=schedule` exists and `conclusion=success` | scheduled run observed | verify artifacts |
| `event=schedule` exists and failed/cancelled | scheduled run failed | inspect metadata/logs read-only |
| no `event=schedule` run | trigger/observability miss | do not infer artifact failure |

Do not use manual workflow dispatch, rerun, or workflow changes for this observation.

## Artifact Verification

`weekly-artifact-local-verify` checks local or downloaded artifacts for required report files, v104 `status.json`,
`gmail_send_attempted=false`, and required copy markers.

If a GitHub artifact is downloaded for inspection, use `/private/tmp` and do not commit downloaded report data.

## Email Preview vs Gmail Delivery

- `email_preview.txt`, `email_preview.html`, and `email_preview.eml` are preview artifacts.
- Preview artifacts are inspection outputs, not proof of Gmail delivery.
- Real Gmail send remains NO-GO unless explicitly approved in a future task.

## Monthly Review Pack

Use `monthly-review-pack-integration` to confirm that:

- Monthly Decision Sheet v84 has required sections and safety wording.
- Monthly Input Consistency v95 is connected to the same fixture month.
- Portfolio Data Quality Review v109 stays fixture/sanitized-input only.
- Target Allocation Gap v82 is represented.
- actual import, broker API, raw Excel direct parsing, and cache write remain NO-GO.

## Language Rules

Use `report-ux-language-contract` before changing user-facing report wording.

Key interpretation rules:

- Candidates and monthly stances are not trade instructions.
- High-priority review means review order, not execution permission.
- ERROR/WARN/INFO are validation severities, not action recommendations.
- email preview artifacts are not Gmail delivery.
- actual import / broker API / raw Excel direct parsing / cache write remain NO-GO.

## Forbidden Actions

Do not execute:

- workflow change or `.github/workflows` edit
- manual workflow_dispatch or rerun
- live HTTP / market-data live fetch
- cache write or cache directory creation
- actual refresh/import or manual import
- broker API, broker login, raw broker export parsing
- raw Excel direct parsing
- env/secret display
- dependency / pyproject / Makefile changes
- trading action, order placement, automated trading
- real email send

## Related Docs

- `docs/sample_output_regeneration.md`
- `docs/progress_dashboard.md`
- `MILESTONE_REPORT.md`
- `docs/decisions/2026-06-05_weekly_artifact_local_verification_harness.md`
- `docs/decisions/2026-06-05_monthly_review_pack_integration_hardening.md`
- `docs/decisions/2026-06-05_report_ux_language_contract.md`
