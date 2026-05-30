# US provider current evidence pack operating model

日付: 2026-05-30
ステータス: approved-by-task
関連: v46 US OHLCV Provider Selection Matrix, `RULES.md` §1/§5

## 結論

- v48 は v46 で残した current evidence gap を source-only evidence pack として固定する。
- Current pricing/terms、cache suitability、adjusted price method、ADR/delisted coverage、bulk throughput はすべて `needs_current_recheck=true` とする。
- Tiingo は first pilot candidate、Polygon.io は production candidate、Stooq は fallback のままだが、いずれも live/cache/import は未承認。

## Source-only 境界

| 項目 | v48 の扱い |
|---|---|
| live HTTP | 実行しない |
| provider live access | 実行しない |
| cache write | 実行しない |
| actual refresh/import | 実行しない |
| env/secret 表示 | 実行しない |
| broker/manual raw data | 扱わない |
| workflow/dependency/pyproject 変更 | 行わない |
| trading action | 行わない |

## Evidence confidence

- `evidence_confidence = seed_only / manual_recheck_required`
- `source_accessed_live = false`
- `needs_current_recheck = true`

## 反証

- Provider pricing、terms、rate limits、coverage は変わるため、source-only pack は current verification ではない。
- Seed evidence を verified current evidence と誤読すると、cache storage や production provider selection のリスクが残る。
- 対策として、report と context pack の両方に manual current recheck required を明示する。

## 次アクション

- Tiingo、Polygon.io、Stooq の順に current docs を人間が確認する。
- 確認後、必要なら v44 approval request を使い `public_ohlcv` small pilot を別承認する。
- cache write と actual import は first live pilot の結果レビュー後まで承認しない。
