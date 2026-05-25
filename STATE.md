# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `f6621ca`（#258 forward P3 actions）。
- observation_log **94行** · forward matched=**3** thin · docs_163_hard_pass=**True**。
- portfolio **40%**（P0+P1 · G/H 実行済み）· Gmail sent 2026-05-25。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 96% | thin · P3 usable 未達 |
| portfolio/ | 40% | shadow 2 · resolved_links=2 |
| reports/ui | 85% | thin→post-refresh next_commands |
| data ingest | 75% | MSFT/NVDA/GOOGL/AAPL refreshed |
| operator/ | 82% | Gmail sent_ok（D） |
| risk/ | 62% | — |

## §2. 残作業

- [ ] forward P3 usable（matched≥10 等）
- [ ] stale_cache skips 削減

## §4. 最新ローカル観測

```text
origin/main: f6621ca
observation_log: 94 lines
forward: matched=3 · sample_quality=thin
portfolio: 40% human (P0+P1)
```

## §8. 履歴

- 2026-05-25: wave2 E/F/G/H/D 実行
- 2026-05-25: #258 · #255–#257
