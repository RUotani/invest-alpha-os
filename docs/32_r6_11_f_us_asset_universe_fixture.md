# R6.11-F — US asset universe fixture / metadata

**ステータス**: **main 反映済み**（`adb1879`）。branch CI `25921366337` · main CI `25921579826` — success。

---

## 1. 目的

- `config/us_watchlist.yaml` と R6.11-E 方針を **fixture + pure loader** で固定する
- signals / report 接続前の **symbol · asset_class · role · theme** 契約を確立する

## 2. 非目的

- live HTTP · production cache write · signals 拡張 · report / Veto / portfolio / macro 接続

## 3. ファイル

| パス | 役割 |
|------|------|
| `tests/fixtures/us_equities/us_asset_universe_minimal.json` | 16銘柄（watchlist 相当） |
| `src/invis_alpha_os/data/us_asset_universe.py` | parse / load / index |

## 4. エントリ契約

| キー | 説明 |
|------|------|
| `symbol` | 正規化ティッカー |
| `asset_class` | `us_equity` \| `us_etf` \| `crypto_proxy` |
| `role` | `single_stock` \| `market_proxy` \| `growth_proxy` \| `metals_bridge` \| `rates_proxy` \| `crypto_proxy` 等 |
| `theme` | 観測用テーマラベル |
| `display_name` | 表示名 |
| `enabled` | ユニバース有効フラグ |

## 5. `config/us_watchlist.yaml` との関係

- **YAML**: 運用 watchlist のソース・ingest 順序
- **fixture**: テスト・設計固定用メタデータ（role/theme 付き）
- 将来: loader で YAML → universe 変換は **別フェーズ**（本タスクでは未接続）

## 6. 代表マッピング

| symbol | asset_class | role |
|--------|-------------|------|
| MSFT | us_equity | single_stock |
| SPY | us_etf | market_proxy |
| QQQ | us_etf | growth_proxy |
| GLDM / SLV | us_etf | metals_bridge |
| TLT / TMF | us_etf | rates_proxy |
| MSTR / COIN / MARA | crypto_proxy | crypto_proxy |

## 7. main 反映メモ

- **ブランチ**: `work/r6-11-f-us-asset-universe-fixture`
- **worktree**: `/Users/uotani/Projects/invest-alpha-os-r6-11-f`
- **16 entries**: `us_equity` / `us_etf` / `crypto_proxy` · loader / validator / index / `enabled_us_asset_symbols`
- **非接続**: report / Veto / portfolio / macro · live HTTP · production cache write

## 8. 次候補

- **R6.11-G**: universe-aware US signals preview（optional `--universe-path`）
- **R6.11-H**: ETF 向け追加 fixture / golden
