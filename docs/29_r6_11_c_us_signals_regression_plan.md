# R6.11-C — US signals regression / golden test plan（設計のみ）

**ステータス**: 作業ブランチ `work/r6-11-c-us-signals-regression-plan` のみ。**`main` 未反映**。本フェーズは **docs-only** — **追加実装なし**。

---

## 1. 目的

- R6.11-B **`compute_us_cache_signal_row`** の出力契約を、R6.10-H と同様の **golden-style** で固定する計画を文書化する
- 次フェーズ（R6.11-D CLI 等）の受け入れ条件を先に定義する

## 2. 前提（R6.11-B 完了時点）

| 項目 | 状態 |
|------|------|
| Pure helper | `us_cache_signals.py` |
| キー契約 | `US_CACHE_SIGNAL_ROW_OK_KEYS` |
| 単体テスト | `tests/test_us_cache_signals.py`（5件） |
| Fixture | `minimal_msft_envelope` · `msft_25bars_metrics_envelope` |

## 3. R6.11-C 本実装候補（次ブランチ）

### 3.1 Golden-style JSON

- `msft_25bars`: `status=ok`, `momentum_label=uptrend_aligned`, `return_5d` / `return_20d` 固定値
- `minimal_msft`: `status=skipped_insufficient_bars`, `momentum_label=null`

### 3.2 異常系 fixture

- empty envelope · symbol mismatch · `bar_count` 不整合（metrics 層と同パターン）

### 3.3 CLI debug（R6.11-D）

- `debug us-cache-signals-preview --path ... --format json|markdown`
- metrics CLI と同型の **`live_http: false`** 契約

## 4. 非目的

- live HTTP / production cache write
- report / Veto / portfolio 接続
- `momentum_label` 閾値の本格チューニング（観測ラベルは B で最小固定）

## 5. 受け入れ条件（たたき台）

- focused + full pytest 緑 · branch CI success
- 既存 metrics / preview golden **非破壊**
