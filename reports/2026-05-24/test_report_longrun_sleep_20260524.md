# Test Report — longrun_sleep_20260524

## 3行サマリー
- PR #245: **1055 passed**（+1 test: peer_sync_forward in observation-health）。
- PR #246: **1055 passed**（+1 test: ops-smoke docs/160 link）。
- 再現: `.venv/bin/python -m pytest -q`

<<< COPY FROM HERE >>>
# Test Report — longrun_sleep_20260524

## Summary
- status: PASS
- branches: #245 `1041ec3`, #246 `6a66df1`
- python: 3.x (project .venv)

## Commands
```bash
.venv/bin/python -m pytest -q tests/test_observation_health.py
.venv/bin/python -m pytest -q tests/test_ops_smoke_report.py tests/test_product_weekly_us_observation.py
.venv/bin/python -m pytest -q
```

## Results
- PR #245 targeted: 11 passed
- PR #245 full suite: 1055 passed in ~9s
- PR #246 targeted: 19 passed
- PR #246 full suite: 1055 passed in ~9s

## Failures
| Test | Cause | Fix | Rerun |
|---|---|---|---|
| (none) | — | — | — |

## Safety
- operator changes: no
- live HTTP/cache write/Gmail: no
- outputs/cache/secrets: no
- default behavior: unchanged
- workflows/Makefile/pyproject: untouched

<<< COPY TO HERE >>>
