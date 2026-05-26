# US forward P3 stall diagnosis — Final Report（2026-05-26）

## 結論

**normal matched=3/10 が増えない理由**を、行別・銘柄別・P3バケット別に **read-only で機械可読化**した（PR 作成待ち: `work/us-forward-p3-stall-diagnosis`）。

---

## US forward 3/10 停滞の原因分類（ローカル log 514 · read-only）

| 分類 | 典型件数イメージ | 説明 |
| --- | --- | --- |
| **insufficient_future** | 大半 | cache 内に event はあるが 60d horizon 用の未来バー不足 |
| **stale_cache_horizon** | 少数（履歴16） | event > cache 末尾 · 再ログしても履歴行は戻らない |
| **duplicate_same_week_rows** | 要監視 | 同一銘柄・同一 ISO 週の重複ログ |
| **unmatchable_as_of** | 少数 | event が cache 範囲外 |
| **missing_cache** | tier-1 欠損時 | price JSON 無し |
| **parse_invalid** | 非 US 行等 | pre_skipped |

**P3 バケット**

| バケット | 意味 |
| --- | --- |
| `matchable_now` | normal で既に matched（現状 **3**） |
| `will_be_matchable_after_date` | カレンダー経過で増える（weekly+as_of 有効） |
| `needs_new_cache_after_date` | P10 等で cache 延長が必要 |
| `dead_rows_or_duplicate_rows` | 重複・パース・復旧不能 stale |

**backtest 416 vs normal 3**: backtest は cache 内へイベントをシフトする探索のみ · **P3 milestone 不可**。

---

## 追加・変更した診断項目

- 新規: `compute_us_forward_p3_stall_diagnosis()` · `format_p3_stall_diagnosis_markdown()`
- 埋め込み: `validate us-forward-returns` / `forward-p3-status` / `portfolio.readiness` P3 detail
- JSON キー: `p3_stall_diagnosis`（`why_matched_stuck`, `p3_bucket_counts`, `by_symbol`, `next_actions`）

---

## P3 usable までの残件

- **samples_needed_for_usable: 7**（10 − matched_normal 3）
- weekly が有効なのは主に `will_be_matchable_after_date` 行 · 無効なのは duplicate / stale 履歴 / dead

---

## テスト

```text
pytest tests/test_product_us_forward_return_validation.py \
  tests/test_forward_p3_status.py \
  tests/test_post_p10_refresh_smoke.py \
  tests/test_portfolio_readiness.py -q
→ 46 passed
```

---

## Safety

- live HTTP / cache write / Gmail: **未実行**
- operator/ 増築: **なし**
