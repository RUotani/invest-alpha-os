# Test report — Weekly Observation Report v1

日付: 2026-05-27

## Targeted

```bash
.venv/bin/python -m pytest tests/test_weekly_observation_report_v1.py -q
```

結果: **5 passed**

## Full suite

```bash
.venv/bin/python -m pytest -q
```

結果: **1157 passed, 4 failed** (327s)

### Failures (pre-existing / unrelated to v1)

| test | 備考 |
| --- | --- |
| `test_jquants_client.py::test_debug_jquants_status_never_calls_urlopen` | env/mock |
| `test_jquants_client.py::test_debug_jquants_status_output_masked` | env/mock |
| `test_us_provider_cache_preview.py::test_live_get_url_omits_placeholder_apikey_when_stooq_env_unset` | env |
| `test_us_signals_report_opt_in.py::test_daily_flagless_matches_golden_fixed_date_and_watchlist_stub` | golden date |

v1 PR スコープ外。product 変更に対する回帰は targeted + 関連 product tests で確認済み。

## Related product tests (local)

```bash
.venv/bin/python -m pytest tests/test_weekly_observation_report_v1.py \
  tests/test_product_weekly_us_observation.py \
  tests/test_portfolio_readiness.py \
  tests/test_observation_health.py -q
```

結果: **pass** (v1 + weekly + portfolio + health)
