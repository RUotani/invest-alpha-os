# R6.12-A — US signals report dry-run MVP

**ステータス**: **main 反映済み**（`6545bbf`）。branch CI `25922379413` · main CI `25922649486` — success。

---

## 1. 目的

- R6.11-G/H の US cache signals preview を **report 向け Markdown section** として dry-run 出力する
- 単一 symbol / fixture ベースの最小 MVP
- **既存 daily report 本体には未接続**

## 2. 非目的

- daily report デフォルト接続 · Gmail/PDF · Veto / portfolio / macro
- live HTTP · production cache write · 複数 symbol バッチ

## 3. API

| 関数 | 役割 |
|------|------|
| `render_us_cache_signals_dry_run_section(preview)` | preview dict → dry-run Markdown section |

入力は `build_us_cache_signals_preview`（+ 任意で `attach_us_asset_universe_metadata_to_signals_preview`）の出力。

## 4. Output contract

- 見出し: `## US Signals Dry Run`
- 免責: observation only · dry-run · not buy/sell · daily report 未接続
- 表: Symbol · Asset · Role · Signal · 20d · 5d · Universe
- 補足行: display_name / theme / status+reason（該当時）· live_http: false

## 5. 既存 formatter との関係

- `format_us_cache_signals_preview_markdown`: CLI 診断用（箇条書き）
- `render_us_cache_signals_dry_run_section`: report dry-run 用（表形式）
- 意図的な重複（用途分離）

## 6. 次候補

- **R6.12-B**: multi-symbol dry-run renderer
