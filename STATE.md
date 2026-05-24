# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `7f2101e`（#236 portfolio readiness evaluator + observation enrichment マージ済）。
- observation_log **38行**（US 32 + peer_sync 6 · 週次蓄積 2回目完了）。
- forward: 通常 matched=0（cache stale · 想定内）· `snapshot observation-health` に P0–P3 readiness 表示。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 90% | enriched checklist · weekly_trend · dry-run log read |
| risk/ | 62% | veto-at-t join |
| portfolio/ | [要確認]% | docs/154 auto-evaluator (#236) · % 人間承認待ち |
| data ingest | 64% | US16 cache; tier-1 AMD gap |
| reports/ui | 64% | runbooks 150–163 · observation-health readiness block |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] observation_log 週次蓄積 ×2（2026-05-24 承認済）
- [ ] 週次 observation_log 継続（次回 · 承認）
- [ ] US tier-1 refresh（実行禁止 · P10 別承認 · docs/162）
- [x] program review fix plan PR1–5
- [x] P10 evidence pack docs（#233 · docs/162–163）
- [x] portfolio readiness auto-evaluator（#236 · docs/154 code）
- [ ] portfolio % 確定（docs/154 · 人間承認）

## §4. 最新main

```text
origin/main: 7f2101e
open PRs: 0
tests: 1043 passed
ruff: clean
observation_log: 38 lines (local outputs/)
ops-smoke --strict: exit 2 (repeat/stale · 想定内)
portfolio.readiness: P0 passed · P1–P3 blocked (expected)
tier-1 missing: AMD
```

## §7. 次の推奨

1. 週次 read-only: `docs/160` · `validate ops-smoke --strict` + `snapshot observation-health`
2. 次回週次蓄積: 人間承認後 `--write-observation-log`
3. P10 tier-1 cache refresh（別承認 · docs/162）→ post smoke `docs/163`

## §8. 履歴

- 2026-05-24: #236 portfolio readiness + observation enrichment
- 2026-05-24: #233–#235 docs/162–163 + STATE sync
