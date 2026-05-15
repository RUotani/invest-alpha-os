# R6.13-A — daily integrated US opt-in golden

**ステータス**: **完了・`main` 反映済み**（merge commit `6ab8db1` · branch CI `25944357356` success · **`main` push CI `25944670951` success**）

---

## 1. 目的

- **JQ watchlist 節 ON** · **momentum cache + mixed ON** · **`--us-signals-dry-run-manifest` 指定時**の **見出しレベル順**をテストで固定する
- manifest 未指定時は **US opt-in 節が出ない**こと（同時 ON 設定下）を確認する

## 2. 非目的

- daily 本文の default 変更 · product code 変更 · config 新設
- live HTTP · production cache write · Veto / portfolio / macro

## 3. テスト方針（パターンA）

- `tests/test_daily_report_integrated_us_opt_in_golden.py`
- `config/*.yaml` を **テンポラリにコピー**し `CONFIG_DIR` / `paths.CONFIG_DIR` を向け先変更（`veto_rules.yaml` 欠如を回避）
- `watchlist.yaml` のみ **単一銘柄**に上書き（簡潔な JP 件数）
- `ROOT_DIR`（JQ）は **REPO_ROOT** に固定して smoke Markdown のパス既定を再利用
- アサート: **`## J‑Quants` < `## Momentum — Cache Only` < `## Momentum — Mixed` < `### US Signals Dry Run (opt-in)`**

## 4. 非目標メモ

- PDF/Gmail 幅 · 実行時 watchlist と同一の字数 golden（本項は順序ロックのみ）

## 5. 完了検証サマリ

- **ブランチ**: `work/r6-13-a-daily-us-opt-in-integrated-golden`
- **`main` に fast-forward で反映**したコミット: `6ab8db1146a6a82d53dd28ca699c1cf0087837e3`
- **テスト**: focused（US opt-in／momentum／manifest／integrated golden 系）**37 passed** · full pytest **694 passed** · `make agent-final-check` success · live HTTP／production cache write／Veto・portfolio・macro なし

## 6. 次候補

- **R6.13-B**: US report opt-in **operational readiness**（runbook・invalid manifest 期待挙動・smoke。作業ブランチ `work/r6-13-b-us-report-opt-in-operational-readiness`）
