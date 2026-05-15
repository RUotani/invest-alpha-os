# R6.12-F — US report opt-in hardening design

**ステータス**: **完了・main反映済み**（`2b2c1f7` · branch CI `25925044617`）。実装強化は **R6.12-G**。

---

## 1. 目的

- R6.12-E（`--us-signals-dry-run-manifest`）実装後の hardening 計画を固定する
- default daily 出力の回帰検知方針 · invalid manifest UX · 将来 PDF/Gmail 幅

## 2. 非目的

- 実装 · default 出力変更 · config flag 追加 · Veto / portfolio / macro

## 3. default output snapshot

- `tests/test_us_signals_report_opt_in.py` の **二重 invoke 同一性** を CI で維持
- 将来: golden file（flag なし daily 先頭 N 行）を fixture 化（R6.13 候補）

## 4. invalid manifest UX

- 現状: `*(dry-run skipped: manifest_invalid)*` · exit 0
- 改善候補: `reason` 列挙（`manifest_invalid` / `entry_cache_missing`）を1行に限定

## 5. Markdown / 配信

- opt-in 節は `###` 見出しで JP/US momentum 節と階層分離
- PDF/Gmail 化時は表列幅・footnote 折り返しを別途レビュー

## 6. 二重フラグ防止

- **CLI のみ**を main 反映まで維持（`config/us_report.yaml` は R6.13-A 以降）

## 7. dry-run 誤解防止

- 節内に **dry-run only / not buy/sell advice** を維持
- 本番シグナル列との見出し混同を避ける（`US Signals Dry Run` 固定）

## 8. 次候補

- **R6.13-A**: golden snapshot + config opt-in（任意）
- **R6.12-E main 反映**（ChatGPT 判断後）
