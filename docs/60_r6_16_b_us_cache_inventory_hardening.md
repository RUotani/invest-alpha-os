# R6.16-B — US cache inventory summary hardening

**ステータス**: **完了・`main` 反映済み**（PR **#8** · `a34562f`）。

## 目的

R6.16-A inventory MVP に **operator 向け summary** を追加し、watchlist 単位の充足状況を一目で把握できるようにする。

## 変更（後方互換）

- JSON に **`summary`** ブロック追加（`total_symbols` · 各 status count · `cache_root` · optional `watchlist_path`）
- Markdown に **### Summary** セクション追加（`status_counts` / `rows` は維持）
- row **`reason`** を安定コードに統一（`missing_file` · `invalid_cache_payload` · `insufficient_bars` · `stale_unknown` · `ok`）

## 非目的

- live HTTP · production cache write · fetch 実装
- daily report default / US signals default 変更
- R6.16-C operator-gated ingest

## 次候補

- **R6.16-C**: [operator-gated ingest design](./61_r6_16_c_operator_gated_ingest_design.md)（**実装は別承認**）
- **R6.17**: daily 接続判断
