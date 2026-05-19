# R6.16-E — US cache inventory freshness extension

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-16-e-us-cache-inventory-freshness`**。

## 目的

inventory の **`status=ok`**（cache 妥当性）と **`fresh_enough`**（投資判断向け鮮度）を分離する。read-only · live HTTP / cache write なし。

## row 追加フィールド

| フィールド | 値 |
|---|---|
| `latest_date` | 最終 bar 日付（通常 `last_date` と同値） |
| `freshness_status` | `fresh_enough` · `stale` · `freshness_unknown` · `not_applicable` |
| `freshness_reason` | 安定コード |

## summary 追加フィールド

- `fresh_enough_count` · `stale_count` · `freshness_unknown_count`
- `freshness_cutoff_date` · `freshness_reference_date` · `freshness_fresh_days`
- `oldest_latest_date` · `newest_latest_date`

## 初期しきい値

```text
fresh_enough ⇔ latest_date >= reference_date - 7 calendar days
```

`reference_date` 省略時は **実行日（local date）**。

## `not_applicable`

`status` が `missing` · `invalid` · `insufficient` の行は鮮度判定対象外。

## 非目的

- live HTTP · cache write · ingest plan CLI
- daily / US signals default 変更

## 関連

- [docs/59](./59_r6_16_a_us_cache_inventory_mvp.md) · [docs/62](./62_r6_16_d_us_cache_full_population_status.md)（main 未反映の場合あり）
- [docs/61](./61_r6_16_c_operator_gated_ingest_design.md) §3 `ok` vs `fresh enough`
