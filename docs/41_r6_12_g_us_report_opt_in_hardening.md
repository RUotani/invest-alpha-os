# R6.12-G — US report opt-in golden / invalid UX hardening

**ステータス**: 作業ブランチ `work/r6-12-g-us-report-opt-in-hardening` のみ（**`main` 未反映**）。

---

## 1. 目的

- `daily` **flag なし**の本文を日付・watchlist 読みを固定して **golden 照合**する
- `--us-signals-dry-run-manifest` 有効時の **見出し → 免責 → 表** の順序を固定する
- `append_us_signals_dry_run_section` の **invalid manifest appendix** を完全一致スナップショットする

## 2. 非目的

- default daily 本文の変更 · config flag · live HTTP · cache write
- `us_signals_dry_run.py` renderer の契約変更 · Veto / portfolio / macro

## 3. Tests

- `_daily_body` が **書き込み先ファイル**を `cli_main.today_jst_iso()` で読み戻す（テストの日付ずれ防止）
- `_GOLDEN_DAILY_BODY_NO_OPTS` — J‑Quants stub 無効環境 · 空 watchlist
- `_INVALID_APPENDIX_SNAPSHOT` — `manifest_invalid` 短い appendix

## 4. Architecture note

- golden は **環境ヒモ付き文言**（J‑Quants 行のみ）・watchlist は **YAML stub** で **`Watchlist count: 0`** に固定
- 将来 `watchlist.yaml` や stub 説明文が変わる場合は golden のみ更新対象とする（本番運用ログではない）

## 5. 次候補

- **R6.13-A**: full daily と momentum ゲート両立時の順序確認 · golden 拡張（任意）
