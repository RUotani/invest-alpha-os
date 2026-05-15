# R6.10-E — US cache-only basic metrics MVP

**ステータス**: **main 反映済み**（`a7fd315`）。branch CI `25918535243` — success。

---

## 1. 目的

- 検証済み **`list[DailyBar]`** から **基本メトリクス**を **pure function** で算出
- 将来の US signals / report 接続前の土台（**live HTTP なし**）

## 2. 方針（パターンA）

- **`compute_us_daily_bars_basic_metrics`**（`src/invis_alpha_os/data/us_daily_bars_metrics.py`）
- リターン計算は既存 **`calculate_returns`**（JP momentum と同式: `C[-1]/C[-(h+1)]-1`）を再利用

## 3. 非目的

- US scoring / VetoEngine / daily report / portfolio / macro 接続なし
- live HTTP / production cache write なし

## 4. 出力 keys（`status == ok`）

| key | 説明 |
|-----|------|
| `bar_count` | 本数 |
| `first_date` / `last_date` / `latest_date` | 期間 |
| `last_close` / `last_volume` | 直近 |
| `total_return` | `close[-1]/close[0]-1`（2本以上・先頭close≠0） |
| `return_5d` / `return_20d` | 6本以上 / 21本以上で算出可能 |
| `has_5d` / `has_20d` | 各ホライズン算出可否 |

空リストは `status: invalid`, `reason: empty_bars`。

## 5. テスト方針

- 合成 25 本バーで `return_5d` / `return_20d`
- `minimal_msft_envelope.json` で不足ホライズン
- `urlopen` ブロック
