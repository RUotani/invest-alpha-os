# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-25

## 3行サマリー
- `origin/main` @ `8b7a34d`（#253–#254 · P2 supplemental · forward_fresh_log checklist）。
- observation_log **74行** · forward P3 未達（fresh_log）· tier-1 clear。
- portfolio **25%** · P1: `docs/165` shadow seed（手動）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 95% | forward_fresh_log · weekly_trend supplemental |
| portfolio/ | 25% | shadow_seed_hint |
| reports/ui | 81% | post-refresh-smoke in ops next_commands |
| data ingest | 68% | — |
| risk/ | 62% | — |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [ ] forward P3 usable
- [ ] portfolio P1 shadow 配置

## §4. 最新main

```text
origin/main: 8b7a34d
tests: 1067 passed (CI)
observation_log: 74 lines
forward: matched=0 · skip_pattern=fresh_log
```

## §7. 次の推奨

1. `docs/165` shadow seed → P1
2. セッション経過後 `validate us-forward-returns`
3. `validate post-refresh-smoke`

## §8. 履歴

- 2026-05-25: #254 forward_fresh_log · #253 P2/post_refresh/shadow
- 2026-05-25: #251–#252 · 承認 A/B/C
