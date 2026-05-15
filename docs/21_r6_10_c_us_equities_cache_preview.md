# R6.10-C — US equities cache-only preview / diagnostics

**ステータス**: **main 反映済み**（`ec5a2af`）。branch CI `25917974312` — success（main CI run ID は完了 docs コミット後に追記）。

---

## 1. 目的

- R6.10-A/B の **cache-only** レイヤーを、fixture / cache JSON から **短く preview** する
- **live HTTP（実ネットワーク接続）なし**で診断可能にする
- 将来の US signals / reports / portfolio 連携前の入口とする

## 2. 方針（パターンA）

- **`debug us-daily-bars-cache-preview`** CLI（`src/invis_alpha_os/cli/main.py`）
- data 層 helper: **`build_us_daily_bars_cache_preview`** · **`format_us_daily_bars_cache_preview_markdown`** · **`format_us_daily_bars_cache_preview_json`**

## 3. 非目的

- live HTTP / production cache write / `.env` / API キー参照なし
- 本格 US scoring / portfolio / macro / metals なし
- 日次レポート大規模統合なし

## 4. preview 項目

| 項目 | 説明 |
|------|------|
| `validation_status` | `ok` / `invalid` |
| `symbol` | 正規化済みシンボル |
| `bar_count` | バー本数 |
| `first_date` / `last_date` | 期間 |
| `last_close` / `last_volume` | 直近値 |
| `source` | cache メタ |
| `path` | 読み込みパス |
| `live_http` | 常に `false` |

## 5. CLI 例

```bash
python -m invis_alpha_os.cli.main debug us-daily-bars-cache-preview \
  --path tests/fixtures/us_equities/minimal_msft_envelope.json --format markdown

python -m invis_alpha_os.cli.main debug us-daily-bars-cache-preview \
  --path tests/fixtures/us_equities/minimal_msft_envelope.json --format json
```

## 6. テスト方針

- fixture ベース（`minimal_msft_envelope.json`）
- path not found / symbol mismatch / markdown / json 出力
- live HTTP 禁止（`urlopen` ブロック）
