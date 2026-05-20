# Codex — R6.17 post-merge review prompt（read-only)

**Do not implement.** Review **main** integration after PR #16 / #17 / #18.

## Artifacts

- [docs/65_r6_17_opt_in_us_cache_preview_plan.md](../docs/65_r6_17_opt_in_us_cache_preview_plan.md)
- [docs/67](../docs/67_r6_17_opt_in_us_cache_preview_implementation.md)
- [docs/68](../docs/68_r6_17_a_opt_in_us_cache_preview_smoke.md)
- [docs/69](../docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md)
- [docs/70–72](../docs/70_r6_17_c_operational_readiness.md)（if merged）
- `src/invis_alpha_os/reports/us_cache_preview_opt_in.py`
- `tests/test_us_cache_preview_opt_in.py`

## Review questions

1. Is **default still off**（no `--us-cache-preview` → no preview section）?
2. Is **runbook** clear for operator opt-in?
3. Is **stale refresh** separated from **default enablement**?
4. Are **live HTTP / cache write** approvals explicit in docs only?
5. Are **trading recommendations** absent from preview output/tests?
6. Are **stale** rows clearly marked (`stale — returns not used`)?
7. Should **default enablement** wait until **stale_count = 0**?

## Settings

- Read-only · concise report · no full diffs/logs
- Use `.agent/codex_review_template.md` format

## Verdict guidance

- **approve** if opt-in boundary holds and docs chain is consistent
- **request-changes** if default leak, missing gates, or unclear stale policy
