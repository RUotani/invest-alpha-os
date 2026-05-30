# US OHLCV pilot approval bundle operating model

日付: 2026-05-30
ステータス: approved-by-task
関連: v39 Provider Approval Package, v41 Safe Execution Harness, v43 Runbook, v44 Approval Request, v46 Selection Matrix, v48 Current Evidence Pack

## 結論

- v49 は Tiingo first pilot を実行可能にするための source-only approval bundle であり、実行ではない。
- Approval phrase は `public OHLCV source live fetchを実行してよい` の1つだけを primary とする。
- この phrase が将来与えられても unlock されるのは live-fetch-only pilot だけで、cache write / actual import / manual import / trading action は別承認のままにする。

## Tiingo を first pilot にする理由

- v46 で Tiingo は cost、implementation effort、pilot fit のバランスから first pilot candidate とされた。
- v48 で current evidence は seed-only と整理され、pricing/terms/cache/adjustment/coverage/bulk は manual current recheck required とされた。
- したがって v49 は Tiingo を approved provider にはせず、human approval review 用の bundle に留める。

## 承認境界

| 項目 | v49 の扱い |
|---|---|
| public OHLCV source live fetch | future approval phrase 後の別タスクのみ |
| cache write | 未承認 |
| actual refresh/import | 未承認 |
| manual actual import | 未承認 |
| J-Quants refresh | 未承認 |
| broker/manual raw data | 扱わない |
| env/secret 表示 | 行わない |
| workflow/dependency/pyproject 変更 | 行わない |
| trading action | 行わない |

## ChatGPT / Codex / Cursor handoff

- ChatGPT は bundle を見て approval phrase、scope、not-approved actions をレビューする。
- Codex は source-only bundle、tests、CLI/report/context pack integration を維持する。
- Cursor/local は別の明示承認タスクでのみ future live-fetch-only pilot を扱う。

## 反証

- Approval bundle が実行指示に見えると危険。
- 対策として command は `NOT EXECUTED` marker 付きにし、Cursor handoff は draft-only と明示する。
- Current evidence は verified current docs ではないため、manual current recheck を残したまま readiness verdict を conservative にする。

## 次アクション

- Human は Tiingo current docs を確認し、scope が妥当なら primary approval phrase を別タスクで明示する。
- 最初の future task は live-fetch-only に限定し、cache write と actual import は結果レビュー後まで分離する。
