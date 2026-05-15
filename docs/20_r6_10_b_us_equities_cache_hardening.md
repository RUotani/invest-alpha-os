# R6.10-B — US equities cache-only layer hardening（validation / fixtures）

**ステータス**: **main 反映済み**（`e37c38f`）。branch CI `25917456523` · main CI `25917862396` — いずれも success。

---

## 1. 目的

R6.10-A の **`parse_us_daily_bars_payload`** / **`load_us_daily_bars_json_file`** を、**live HTTP（実ネットワーク接続）なし**で信頼性を上げる。

## 2. 実施内容（パターンA）

- **`_us_daily_bar_rows_valid`**: 行が dict・日付非空・日付重複なし・**昇順日付**
- **`bar_count`** が整数のとき **`len(bars)` と一致**必須
- **`tests/fixtures/us_equities/minimal_msft_envelope.json`** 追加
- **`tests/test_us_equities_cache.py`** に edge case テスト追加

## 3. 非目的

- live HTTP / production cache write / CLI・report 統合 / US scoring 本実装

## 4. validation 仕様（追加分）

| 項目 | 挙動 |
|------|------|
| 空 `bars` | `None` |
| 重複 `date` | `None` |
| 日付が昇順でない | `None` |
| `bar_count` ≠ `len(bars)` | `None` |
| 余剰ルートキー / 禁止文字列 | `None`（R6.10-A 同様） |
| 非数値 OHLCV | `bars_from_rows` 失敗 → `None` |
