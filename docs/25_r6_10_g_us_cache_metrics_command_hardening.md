# R6.10-G — US cache metrics command hardening

**ステータス**: **main 反映済み**（`47d95b8`）。branch CI `25919232539` — success。

---

## 1. 目的

- **`debug us-daily-bars-cache-metrics`** の JSON / Markdown 出力契約と異常系を固定
- **`us-daily-bars-cache-preview`** のデフォルト出力は非変更

## 2. 方針（パターンA）

- **`METRICS_PREVIEW_INVALID_BASE_KEYS`** 追加
- CLI 回帰テスト拡充（path / symbol mismatch / invalid envelope / 25本 bars）

## 3. 非目的

- live HTTP / production cache write / US scoring / report 接続なし

## 4. 責務分担

| コマンド | 役割 |
|----------|------|
| `us-daily-bars-cache-preview` | validation / 期間 / OHLCV 概要 |
| `us-daily-bars-cache-metrics` | リターン系 metrics（本タスクで hardening） |
