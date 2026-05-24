# Current Progress Snapshot — 2026-05-24

## 3行サマリー

- 総合の単一%は表示しない。`RULES.md §16` に従い、ドメイン別進捗で見る。
- 現在の中心課題は **portfolio % の人間承認** と **P10 tier-1 refresh 別承認**（docs/162–163 整備済）。
- `origin/main` @ `0b78da0`（#233 マージ済）· observation_log 38行 · ops-smoke `--strict` exit 2 は想定内。

---

## Progress

| ドメイン | 進捗 | 現状 |
| --- | ---: | --- |
| signals/ | 88% | as_of notes、peer_sync × forward まで到達 |
| risk/ | 62% | veto-at-t join 実装済み |
| portfolio/ | [要確認]% | rubric は docs/154、進捗率は人間承認待ち |
| data ingest | 64% | US16 cache、tier-1 **AMD** gap 残り |
| reports/ui | 62% | runbooks 150–163、ops-smoke strict 週次既定 |
| operator/ | 80% | 凍結。追加機能より投資ロジック優先 |

---

## 現在の残作業

1. portfolio readiness rubric の人間承認
2. 次回週次 observation_log 蓄積の承認
3. P10 tier-1 cache refresh の別承認（pre: docs/162 · post: docs/163）
4. `validate ops-smoke --strict` と `snapshot observation-health` の継続運用

---

## Read-only smoke（2026-05-24）

| チェック | 結果 |
| --- | --- |
| ops-smoke | all_ok=False · repeat=16 · forward_stale=1 |
| ops-smoke --strict | exit 2（正常） |
| us-forward-returns | matched=0 · empty |
| peer-sync-forward | 2/6 matched · thin |
| tests | 1033 passed |

---

## 注意

- 単一の総合進捗率は出さない。Goodhart 化と Ops 偏重を避けるため。
- `portfolio/` は `[要確認]%` のまま維持。rubric docs ができても、人間承認前に数値化しない。
