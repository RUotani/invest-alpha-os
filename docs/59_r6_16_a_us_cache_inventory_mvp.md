# R6.16-A — US daily bars cache inventory MVP

**ステータス**: **ブランチ作業のみ**（**`main` 未反映**）。ブランチ: **`work/r6-16-a-us-cache-inventory-mvp`**。

## 目的

US daily bars cache を **read-only** で棚卸しする最小 MVP。watchlist 単位に **file_exists / status / bar_count / 日付範囲** を一覧する。

## 非目的

- live HTTP · production cache write
- US signals / daily report の default 接続変更
- Veto / portfolio / macro
- R6.16-B 以降の operator-gated ingest 実装

## CLI

```bash
invis-alpha-os debug us-daily-bars-cache-inventory \
  --cache-root outputs/market_data/us_daily_bars \
  --format markdown
```

オプション:

- `--watchlist-path` — 省略時は `config/us_watchlist.yaml`（`--symbol` 未指定時）
- `--symbol` — 繰り返し指定で watchlist を上書き
- `--format json|markdown`

## 出力 status

| status | 意味 |
|---|---|
| `missing` | `{cache_root}/{SYMBOL}.json` なし · reason `missing_file` |
| `invalid` | JSON パース / 検証失敗 · reason `invalid_cache_payload` |
| `insufficient` | 有効だが bar 数がシグナル最小未満（&lt; 5） · reason `insufficient_bars` |
| `stale_unknown` | 十分な bar だが freshness メタデータなし · reason `stale_unknown` |
| `ok` | 有効かつ freshness メタデータあり · reason `ok` |

R6.16-B 以降、JSON に **`summary`** 集計ブロックあり（[docs/60](./60_r6_16_b_us_cache_inventory_hardening.md)）。

常に **`source: cache_only`** · **`live_http: false`**。

## 実装

- `src/invis_alpha_os/data/us_daily_bars_cache_inventory.py`
- `debug us-daily-bars-cache-inventory`（`cli/main.py`）
- `tests/test_us_daily_bars_cache_inventory.py`

## 次候補

- **R6.16-B**: validation report hardening
- **R6.16-C**: operator-gated ingest design
- **R6.17**: daily 接続判断（**別承認**）
