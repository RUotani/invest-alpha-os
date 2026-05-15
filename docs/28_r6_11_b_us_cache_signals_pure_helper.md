# R6.11-B — US cache-only signals pure helper MVP

**ステータス**: 作業ブランチ `work/r6-11-b-us-signals-pure-helper-mvp` のみ。**`main` 未反映**。

---

## 1. 目的

- R6.10 metrics を **再利用**し、US 銘柄1件分の **観測用シグナル行**（`dict`）を pure function で生成する
- **cache-only** · fixture テストで回帰可能にする

## 2. API

| 関数 | 役割 |
|------|------|
| `compute_us_cache_signal_row(bars, *, symbol, asset_class=None)` | 検証済み `DailyBar[]` から1行生成 |
| `load_us_cache_signal_row_from_json_file(path, ...)` | envelope JSON 読込 + 上記（parse 失敗は `None`） |
| `US_CACHE_SIGNAL_ROW_OK_KEYS` | 成功行の JSON キー契約 |

## 3. 出力契約（観測のみ・売買指示ではない）

- `status`: `ok` | `skipped_insufficient_bars` | `invalid`
- `momentum_label`: `uptrend_aligned` | `uptrend_short` | `pullback_short` | `neutral` | `None`
- `source`: `cache_only` · `live_http`: `false`
- metrics フィールドは `compute_us_daily_bars_basic_metrics` と整合

## 4. 非目的

- live HTTP / production cache write / CLI / report / Veto / portfolio

## 5. テスト

- `tests/test_us_cache_signals.py`（`minimal_msft_envelope` · `msft_25bars_metrics_envelope`）
