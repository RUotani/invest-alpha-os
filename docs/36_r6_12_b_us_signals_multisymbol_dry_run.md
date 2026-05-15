# R6.12-B — Multi-symbol US signals report dry-run

**ステータス**: 作業ブランチ `work/r6-12-b-us-signals-report-multisymbol-dry-run` のみ。**`main` 未反映**。

---

## 1. 目的

- R6.12-A の単一 symbol dry-run を **複数 preview dict** 対応に拡張する
- 1 つの Markdown section · 1 つの表に複数行
- **既存 `render_us_cache_signals_dry_run_section` の出力契約は非破壊**（内部リファクタのみ）

## 2. 非目的

- daily report デフォルト接続 · 複数 cache path 自動走査 · Veto / portfolio / macro

## 3. API

| 関数 | 役割 |
|------|------|
| `render_us_cache_signals_multi_symbol_dry_run_section(previews)` | preview リスト → 複数行表 + 行別 footnote |
| `render_us_cache_signals_dry_run_section(preview)` | 単一 symbol（R6.12-A 互換） |

空リスト時: `*(no preview rows)*` · 表ヘッダなし。

## 4. Footnote 規約

- 単一 symbol: R6.12-A と同一（prefix なし）
- 複数 symbol: `**{symbol}** · **field**: value` 形式で行を区別

## 5. 次候補

- **R6.12-C**: daily report opt-in 接続設計
