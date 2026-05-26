# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-26

## 3行サマリー
- `origin/main` @ `112a9ea`（#285 P3 L1 write gate · #284 skip duplicate ISO-week）。
- log **538** · peer **usable** · US **1/10** thin（normal）· human **55%** P0-P2。
- バッチ: **L1 消費済み 2/2**（skip 付き最終）· L2/L3 消費済み · P3/70% は usable 後。

## §4. ローカル

```text
observation_log: 538
portfolio human: 55% P0-P2
peer_forward: usable
us_forward: 1/10 thin (normal matched=1)
p3_us_forward_summary: need 9 toward usable
```

## §5. 直近ゲート

| ゲート | 状態 |
| --- | --- |
| `will_be_matchable_after_date_rows` | 16 |
| L1 | **消費済み 2/2** · [skip 実行](../reports/2026-05-26/approved_execution_L1_skip_20260526.md) |
| 重複週方針 | [decision](../docs/decisions/2026-05-26_observation_log_duplicate_week_policy.md) |
| portfolio 70% / P3 | usable 到達後に L3 再承認 |
