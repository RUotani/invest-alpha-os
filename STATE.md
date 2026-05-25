# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `a8fa257`（#261 stale_skip_by_symbol）。
- US **3/10** · peer **6/10** thin · portfolio **40%** P0+P1 · P2 declining（supplemental active）。
- **承認待ち wave3**: I weekly · J P10 stale 銘柄 · K % · L Gmail。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 97% | wave3 I/J 待ち |
| portfolio/ | 40% | P2 hint · P3 3/10 in readiness |
| reports/ui | 88% | p2_weekly_hint in health |
| data ingest | 75% | — |
| operator/ | 82% | — |
| risk/ | 62% | — |

## §2. 残作業

- [ ] 承認 I/J（P3 usable）
- [ ] 承認 K（P2→55% / P3→70% は達成後）

## §4. 最新ローカル観測

```text
origin/main: a8fa257
observation_log: 94 lines
us_forward: 3/10 thin · peer: 6/10 thin
stale_skip_symbols: MSFT,NVDA,AAPL,AMZN,GOOGL,META,…
```

## §7. 次の推奨

1. [approval_requests_wave3_20260525.md](../reports/2026-05-25/approval_requests_wave3_20260525.md) — I/J YES
2. `validate post-refresh-smoke`

## §8. 履歴

- 2026-05-25: #260–#261 · wave2 全実行
- 2026-05-25: wave3 承認リクエスト掲出
