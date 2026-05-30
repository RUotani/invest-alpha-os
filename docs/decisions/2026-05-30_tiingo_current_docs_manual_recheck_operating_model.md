# Tiingo current docs manual recheck operating model

日付: 2026-05-30
ステータス: approved-by-task
関連: v49 US OHLCV Pilot Approval Bundle, v48 Current Evidence Pack, `RULES.md` §1

## 結論

- v52 は Tiingo live-fetch-only pilot の前に必要な current docs manual recheck pack であり、実行承認ではない。
- pricing/plan、terms/redistribution、API limits、adjusted price method、corporate actions、coverage、cache suitability はすべて manual signoff required とする。
- Default verdict は `manual_recheck_required_before_live_fetch` のまま固定する。

## Source-only 境界

| 項目 | v52 の扱い |
|---|---|
| Tiingo API call | 実行しない |
| provider live access | 実行しない |
| public OHLCV source live fetch | 実行しない |
| cache write | 実行しない |
| actual refresh/import | 実行しない |
| manual actual import | 実行しない |
| env/secret 表示 | 行わない |
| broker/manual raw data | 扱わない |
| workflow/dependency/pyproject 変更 | 行わない |
| trading action | 行わない |

## Human signoff

- Human/operator は各 checklist category で current docs を手動確認する。
- Signoff が揃っても、このPR自体は live fetch を承認しない。
- 次の別タスクで approval phrase を明示した場合のみ、live-fetch-only pilot を検討する。

## 反証

- Official docs のseed reference は現在値の証明ではない。
- Pricing、terms、limits、coverage、cache permission は変更され得る。
- 対策として `source_accessed_live=false`、`api_called=false`、`cache_written=false`、`needs_manual_recheck=true` を全項目に付ける。

## 次アクション

- Tiingo pricing、terms、EOD docs、split/dividend docs を人間が確認する。
- signoff が通れば、v49 approval bundle を根拠に別タスクで live-fetch-only approval phrase を出す。
- cache write と actual import は Tiingo live fetch pilot 後のレビューまで分離する。
