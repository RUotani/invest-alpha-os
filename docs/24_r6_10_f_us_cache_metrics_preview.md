# R6.10-F — US cache metrics preview / diagnostics integration

**ステータス**: **main 反映済み**（`13e1b6b`）。branch CI `25918932189`（pre-rebase `8db961a`）— success。

---

## 1. 目的

- R6.10-E **basic metrics** を **cache-only diagnostics** から確認可能にする
- R6.10-C/D **`us-daily-bars-cache-preview`** の **デフォルト出力契約は非変更**

## 2. 方針（パターンB）

- 別コマンド **`debug us-daily-bars-cache-metrics`**
- helper: **`build_us_daily_bars_cache_metrics_preview`** · formatters（`us_daily_bars_metrics.py`）
- **`METRICS_PREVIEW_OK_KEYS`** で JSON 契約を固定

## 3. 非目的

- live HTTP / production cache write / US scoring / report / Veto 接続なし

## 4. CLI 例

```bash
python -m invis_alpha_os.cli.main debug us-daily-bars-cache-metrics \
  --path tests/fixtures/us_equities/minimal_msft_envelope.json --format json
```

## 5. 既存 preview との関係

| コマンド | 役割 |
|----------|------|
| `us-daily-bars-cache-preview` | 検証・期間・直近 OHLCV（R6.10-C/D 契約維持） |
| `us-daily-bars-cache-metrics` | リターン系 metrics（R6.10-E + F） |
