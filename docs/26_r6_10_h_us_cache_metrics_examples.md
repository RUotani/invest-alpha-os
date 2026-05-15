# R6.10-H — US cache metrics examples / regression hardening

**ステータス**: **main 反映済み**（`fa6f1d3`）。branch CI `25919651109` — success。

---

## 1. 目的

- **`debug us-daily-bars-cache-metrics`** の実用 fixture と golden-style 回帰テストを追加
- 25本以上の bars で `return_5d` / `return_20d` が出ることを固定 fixture で再現

## 2. 方針（パターンA）

- 固定 fixture: **`tests/fixtures/us_equities/msft_25bars_metrics_envelope.json`**
  - MSFT · 25本 · 昇順日付 · close 100→124（1日+1）
- JSON / Markdown の主要キー・代表値をテストで固定
- **`us-daily-bars-cache-preview`** のデフォルト出力は非変更

## 3. 非目的

- live HTTP / production cache write / US scoring / report / Veto 接続なし

## 4. CLI 例

```bash
# 2本 fixture（return_5d / return_20d 不足）
python -m invis_alpha_os.cli.main debug us-daily-bars-cache-metrics \
  --path tests/fixtures/us_equities/minimal_msft_envelope.json --format json

# 25本 fixture（return_5d / return_20d あり）
python -m invis_alpha_os.cli.main debug us-daily-bars-cache-metrics \
  --path tests/fixtures/us_equities/msft_25bars_metrics_envelope.json --format markdown
```

### 25本 fixture の期待 metrics（代表）

| キー | 値 |
|------|-----|
| `bar_count` | 25 |
| `first_date` | 2024-01-02 |
| `last_date` | 2024-01-26 |
| `total_return` | 0.24 |
| `return_5d` | ≈ 124/119 − 1 |
| `return_20d` | ≈ 124/104 − 1 |
| `has_5d` / `has_20d` | true |

## 5. preview との違い

| コマンド | 役割 |
|----------|------|
| `us-daily-bars-cache-preview` | 検証・期間・直近 OHLCV（metrics キーなし） |
| `us-daily-bars-cache-metrics` | リターン系 metrics（本タスクで fixture 例を固定） |
