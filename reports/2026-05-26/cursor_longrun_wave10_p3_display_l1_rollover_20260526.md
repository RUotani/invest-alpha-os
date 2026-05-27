# Cursor longrun wave 10 — P3 display + L1 rollover + axis consistency

## 3行サマリー
- PR #302–#304 **merged** on main @ `69c477b`.
- P3 display: raw `rows_matched` ≠ `matched_normal`; `p3_sample_quality: thin` when dedupe=1/10.
- L1: rollover passed + write_now=0 → cache/as_of or duplicate-week wording.

## PRs

| PR | Theme | State | SHA |
| --- | --- | --- | --- |
| [#302](https://github.com/RUotani/invest-alpha-os/pull/302) | forward-p3-status display split | **merged** | squash on main |
| [#303](https://github.com/RUotani/invest-alpha-os/pull/303) | L1 rollover passed wording | **merged** | squash on main |
| [#304](https://github.com/RUotani/invest-alpha-os/pull/304) | matched_normal axis across portfolio/health/smoke/weekly | **merged** | `69c477b` |

## Verification

```bash
.venv/bin/python -m pytest tests/test_product_us_forward_return_validation.py tests/test_forward_p3_status.py tests/test_post_p10_refresh_smoke.py tests/test_portfolio_readiness.py tests/test_observation_health.py tests/test_product_weekly_us_observation.py tests/test_p3_monitoring_commands.py -q
# 82 passed
```

## P3 usable remaining

- `matched_normal=1/10` thin · `samples_needed_for_usable=9`
- L1 blocked until new ISO week write or cache/as_of advance

## Safety

- No live HTTP / cache write / Gmail executed.

## Next session prompt

```
Continue wave 10: merge #304 when CI green; STATE.md small follow-up; then D (risk veto observation summary read-only) if queue allows.
```
