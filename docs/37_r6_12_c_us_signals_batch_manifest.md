# R6.12-C — US signals batch manifest helper

**ステータス**: 作業ブランチ `work/r6-12-c-us-signals-batch-manifest` のみ。**`main` 未反映**。

---

## 1. 目的

- multi-symbol dry-run へ渡す **明示的 batch manifest**（symbol + cache_path 列）を fixture + pure loader で固定する
- ディレクトリ走査・watchlist 自動実行は行わない

## 2. 非目的

- daily report デフォルト接続 · 自動 cache 検出 · live HTTP · production cache write

## 3. Manifest 契約

| キー | 説明 |
|------|------|
| `schema_version` | `1` |
| `entries[]` | `{ "symbol", "cache_path" }`（必須） |
| `universe_path` | 任意 · manifest 全体に適用 |

`cache_path` / `universe_path` は `path_base` からの相対パス（テストでは repo root）。

## 4. API

| 関数 | 役割 |
|------|------|
| `parse_us_cache_signals_batch_manifest_payload` | JSON 検証 |
| `load_us_cache_signals_batch_manifest_json_file` | ファイル読込 |
| `build_us_cache_signals_previews_from_batch_manifest` | manifest → preview リスト |

## 5. R6.12-B との接続

```text
manifest → build_us_cache_signals_previews_from_batch_manifest
         → render_us_cache_signals_multi_symbol_dry_run_section(previews)
```

## 6. 次候補

- **R6.12-D**: daily report opt-in 接続設計
