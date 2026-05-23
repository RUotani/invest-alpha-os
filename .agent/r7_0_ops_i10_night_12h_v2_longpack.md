# R7.0-Ops-I10 Cursor Longpack — Night 12h v2 (skeleton)

**Status**: draft only — do not run 12h until human approves after I9 8h review.

---

## Preconditions

- main at or after I9 daytime 8h merge
- `post-run-review` on latest 8h evidence
- clean tree · no quarantine marker files
- open stacked PRs triaged via `list_productive_stacked_prs.sh`

---

## Queue

- `config/tasks/autonomous_dev_queue_productive_12h_v2.yaml`
- refresh `productive_8h_superseded_tasks.yaml` from I9 failures
- **not** default in `run_productive_true_longrun_12h.sh` until operator enables

---

## Profile

- `true_longrun_12h` · min 720m · max_prs 25 · failure budget 8 / category 4
- consolidation preflight if >N open autonomous PRs

---

## Safety

Same as `.agent/development_automation_contract.md` — no auto-merge, no live HTTP/cache/Gmail, no trading wording.

---

## Final report

Single Markdown code block per `.agent/report_template.md`.
