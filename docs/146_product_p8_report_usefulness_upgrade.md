# Product P8 — Report usefulness upgrade

**Status**: implemented · opt-in only · no default changes

---

## Weekly report

`weekly-us-observation` markdown now includes (when data exists):

- observation_log repeat symbols and signal aging
- structured research checklist (`category`, `symbol`, `reason`, `next_action`)
- forward validation summary (if observation_log has US rows)
- tier-1 US expansion cache gaps

## Daily opt-in

```bash
.venv/bin/python -m invis_alpha_os.cli.main daily --us-observation-summary
```

Appends **US observation usefulness** section (cache-only). Does not enable Gmail or change other daily defaults.

## Research checklist categories

- `repeat_signal`
- `aged_signal`
- `missing_cache`
- `thin_forward_validation`
- `veto_review`

## US 30+ readiness

```bash
.venv/bin/python -m invis_alpha_os.cli.main us-universe-expansion-plan --tier 1 --missing-only
```

Configured target count: **36** symbols in `config/us_universe_expansion_30.yaml`.
