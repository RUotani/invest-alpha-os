# v1.5 Read-Only OHLCV Approval Gate

作成日: 2026-06-06  
関連: #509 fixture metrics · `docs/proposals/v1_5_price_volume_mvp_approval_20260606.md`

## 結論

v1.5 Price/Volume validation は **fixture-only を既定** とし、live read-only fetch は明示承認 phrase が揃うまで Hard Gate で停止する。

## Adapter Modes

| mode | network | cache write | 承認 |
| --- | --- | --- | --- |
| `fixture_only` | 禁止 | 禁止 | 不要 |
| `live_read_only` | gated | 禁止 | 必須 |

## 承認 phrase

```text
承認: v1.5 read-only price/volume MVP validationのみ YES / cache write・broker・trading・import・secret表示 NO
```

## 実装境界

- interface: `V15OhlcvSourceAdapter` in `discovery/v1_5_ohlcv_source_adapter.py`
- default adapter: `FixtureV15OhlcvSourceAdapter`
- gate: `evaluate_v15_readonly_gate()`
- metrics bridge: `build_early_discovery_inputs_from_series()` → `EarlyDiscoveryInputs`

## 停止条件（Hard Gate）

- cache write
- broker API / actual import
- trading / order placement
- raw broker data
- secret / env 表示
- live fetch without explicit phrase
- performance claim への接続

## 次段階（承認後のみ）

1. public read-only source adapter（yfinance 等）
2. no cache write by default
3. local/private validation report only
4. v1.4 fixture classification との比較レポート
