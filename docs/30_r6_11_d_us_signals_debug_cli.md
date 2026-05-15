# R6.11-D — US cache signals debug CLI / golden regression

**ステータス**: 作業ブランチ `work/r6-11-d-us-signals-debug-cli` のみ。**`main` 未反映**。

---

## 1. 目的

- R6.11-B pure helper を **`debug us-cache-signals-preview`** で診断可能にする
- JSON / Markdown 出力と golden-style 回帰を固定する

## 2. CLI

```bash
python -m invis_alpha_os.cli.main debug us-cache-signals-preview \
  --path tests/fixtures/us_equities/msft_25bars_metrics_envelope.json --format json
```

- **`--format`**: `json` | `markdown`
- exit **0**: `status == ok` のみ
- exit **1**: `skipped_insufficient_bars` / `invalid`
- exit **2**: 不正 `--format`

## 3. Helper API

| 関数 | 役割 |
|------|------|
| `build_us_cache_signals_preview` | path → signal row + `path` |
| `format_us_cache_signals_preview_json` | JSON 出力 |
| `format_us_cache_signals_preview_markdown` | Markdown 出力 |
| `US_CACHE_SIGNALS_PREVIEW_INVALID_BASE_KEYS` | 異常系キー契約 |

## 4. 非目的

- live HTTP / production cache write / report / Veto / portfolio

## 5. テスト

- `tests/test_us_cache_signals.py`（preview golden 拡充）
- `tests/test_cli_us_cache_signals_preview.py`
