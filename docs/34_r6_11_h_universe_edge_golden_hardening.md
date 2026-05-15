# R6.11-H — Universe edge-case golden hardening

**ステータス**: **main 反映済み**（`5f546bd`）。branch CI `25922035968` · main CI `25922292372` — success。

---

## 1. 目的

- R6.11-G universe-aware preview の **edge-case** と golden-style regression を固定する
- `disabled` / `not_found` / `invalid` / `skipped_insufficient_bars` + universe の JSON / Markdown 表示をテストで固定する

## 2. 非目的

- live HTTP · production cache write · report / Veto / portfolio / macro 接続
- CLI default 出力契約の変更

## 3. Fixture

| パス | 用途 |
|------|------|
| `us_asset_universe_msft_disabled.json` | MSFT のみ `enabled: false` |

## 4. `asset_class` 優先順位（将来接続向け）

| 条件 | `asset_class` の出所 |
|------|---------------------|
| `--universe-path` なし | envelope / compute 引数のみ（R6.11-D どおり） |
| `--universe-path` あり・`matched` / `disabled` | **universe エントリが preview の `asset_class` を上書き** |
| `--universe-path` あり・`not_found` | envelope 側の値を維持（universe は上書きしない） |

report 接続時は本優先順位を維持し、二重ソースの暗黙マージは行わない。

## 5. Edge-case 契約

- **disabled**: signal status は維持 · metadata（role/theme/display_name/asset_class）は付与 · `universe_status: disabled`
- **not_found**: `universe_status` のみ追加
- **invalid universe**: `status: invalid` / `reason: universe_invalid` · Markdown に `universe_path` 表示
- **skipped + universe**: signal `skipped_insufficient_bars` のまま · matched universe metadata を併記可能

## 6. 次候補

- **R6.12-A**: US signals report dry-run MVP
