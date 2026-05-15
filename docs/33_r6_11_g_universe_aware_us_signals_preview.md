# R6.11-G — Universe-aware US cache signals preview

**ステータス**: **main 反映済み**（`d6221ca` rebase 後 · original `e04cbc7`）。branch CI `25921702389` · main CI `25921938640` — success。

---

## 1. 目的

- R6.11-F の US asset universe metadata を **`debug us-cache-signals-preview`** に任意接続する
- `--universe-path` 指定時のみ `asset_class` / `role` / `theme` / `display_name` / `universe_status` を付与する
- **default 出力契約は非破壊**（`--universe-path` なしでは R6.11-D と同一キー集合）

## 2. 非目的

- live HTTP · production cache write · report / Veto / portfolio / macro 接続
- US score engine 本実装 · ETF signals 本実装

## 3. CLI

```bash
python -m invis_alpha_os.cli.main debug us-cache-signals-preview \
  --path tests/fixtures/us_equities/msft_25bars_metrics_envelope.json \
  --universe-path tests/fixtures/us_equities/us_asset_universe_minimal.json \
  --format json
```

- **`--universe-path`**: 省略時は universe キーを一切付与しない
- exit **0**: `status == ok` のみ（signal 側。universe `not_found` / `disabled` でも signal が ok なら 0）
- exit **1**: signal `skipped` / `invalid`、または universe ファイル invalid（`reason: universe_invalid`）
- exit **2**: 不正 `--format`

## 4. Helper API

| 関数 | 役割 |
|------|------|
| `attach_us_asset_universe_metadata_to_signals_preview` | preview + universe JSON → metadata 合成 |
| `US_CACHE_SIGNALS_UNIVERSE_EXTRA_KEYS` | universe 付与時の追加キー契約 |

## 5. `universe_status`

| 値 | 意味 |
|----|------|
| `matched` | symbol が universe にあり `enabled: true` |
| `disabled` | symbol はあるが `enabled: false`（metadata は付与） |
| `not_found` | symbol 欠落または universe に未登録 |
| （省略） | `--universe-path` 未指定 |

universe ファイル自体が invalid の場合: preview 全体を `status: invalid` / `reason: universe_invalid` に置換（signal 行は返さない）。

## 6. signal status との関係

- universe は **観測メタデータのオーバーレイ**のみ。`momentum_label` / metrics 計算は変更しない
- `skipped_insufficient_bars` + universe 指定時も signal status は維持し、可能なら `universe_status` のみ付与

## 7. 次候補

- **R6.11-H**: universe edge-case golden hardening（disabled / skipped + universe）
- **R6.12-A**: report section dry-run（設計 docs 先行）
