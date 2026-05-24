# Product — portfolio observation progress proposal (Wave C)

**Status**: design proposal · `[要確認]%` unchanged

---

## Current capabilities

- `snapshot portfolio-observation-summary` — linkage + **by_symbol** / **by_tag** exposure counts
- Shadow positions remain manual; no sizing defaults

## Suggested progress rubric (human approval required)

| Milestone | Criteria | Suggested % |
| --- | --- | --- |
| P0 | shadow JSONL + read-only CLI | **done** |
| P1 | thesis_evidence_ids linked to observation_log | partial |
| P2 | weekly `--write-observation-log` sustained | human ops |
| P3 | forward validation `sample_quality=usable` | pending data |
| P4 | observation-only sizing experiment | **not started** |

**Do not auto-update STATE %** until human confirms rubric.

## Read-only commands

```bash
.venv/bin/python -m invis_alpha_os.cli.main snapshot portfolio-observation-summary --format markdown
.venv/bin/python -m invis_alpha_os.cli.main snapshot observation-health --format json
```
