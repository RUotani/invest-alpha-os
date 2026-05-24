# STATE.md — invest-alpha-os 現状スナップショット

版: v0.1 / 最終更新: 2026-05-24

## 3行サマリー
- `origin/main` @ `d10098c`（#238–#239 · tier-1 gap · weekly #3 · AMD blocked）。
- observation_log **58行**（US 48 + peer_sync 10 · 週次蓄積 #3 承認実行済）。
- P10 AMD refresh: **失敗**（`STOOQ_APIKEY` 未設定 · cache 未書込）。

## §1. ドメイン別進捗

| ドメイン | 進捗 | コメント |
|---|---:|---|
| signals/ | 90% | enriched checklist · weekly_trend |
| risk/ | 62% | veto-at-t join |
| portfolio/ | [要確認]% | readiness evaluator · % 人間承認待ち |
| data ingest | 64% | tier-1 **AMD** gap（Stooq API key 要） |
| reports/ui | 66% | observation-health tier-1 line · docs/81 Gmail |
| operator/ | 80% | 凍結 |

## §2. 残作業

- [x] 週次 observation_log #3（2026-05-24 承認実行）
- [ ] P10 AMD refresh 再試行（`STOOQ_APIKEY` 設定後 · docs/162）
- [ ] 週次 observation_log 継続（次回 · 承認）
- [x] docs/81 Gmail runbook
- [ ] portfolio % 確定（人間承認 · `[要確認]` 維持）

## §4. 最新main

```text
origin/main: d10098c
open PRs: 0
tests: 1047 passed
observation_log: 58 lines (local outputs/)
tier-1 missing: AMD (STOOQ_APIKEY blocker)
ops-smoke --strict: exit 2 expected
```

## §7. 次の推奨

1. `STOOQ_APIKEY` を git 外 env に設定 → AMD refresh 再実行（docs/162/163）
2. 週次 read-only: `docs/160` · `snapshot observation-health`（tier-1 gap 行確認）
3. Gmail dry-run: `docs/81` · `./scripts/run_daily_gmail_report.sh --dry-run`

## §8. 履歴

- 2026-05-24: Cursor longrun standard adopted (`.agent/cursor_agent_quality_efficiency_longrun_standard.md`)
- 2026-05-24: #238 tier-1 gap · docs/81; weekly #3 · AMD refresh blocked
- 2026-05-24: #236 portfolio readiness evaluator
