# R7.0-B — JP Universe Scanner MVP

**日付**: 2026-05-20 · **性質**: cache/fixture-only · observation-only

---

## 1. Purpose

JP 銘柄ユニバース入力から **price/volume** のみで **deep-dive candidate** を列挙する MVP。売買推奨ではない。

---

## 2. Scope

| 含む | 含まない |
|---|---|
| ローカル J-Quants cache / YAML universe | live HTTP |
| r1/r5/r20/r60 · volume ratio · 52w high 距離 | reputation/news（R7.0-D） |
| markdown / json 出力 | デフォルト daily/signals 有効化 |
| display name（R6.19-A） | portfolio / macro / Veto |

---

## 3. What it can do

- `discover-jp` CLI で候補テーブルとグループ別サマリを生成
- `discovery_score` でフォローアップ研究の並び替え補助（**not** trading score）

---

## 4. What it cannot do

- 全市場横断を保証しない（入力 universe に依存）
- 売買・配分・注文指示を出力しない
- cache を書き換えない

---

## 5. Universe scope caveat

| `universe_scope` | 意味 |
|---|---|
| `local_cache_available_symbols` | `outputs/market_data/jquants_daily_bars/*.json` のみ |
| `sample_jp_universe` | `--universe-file` で明示したサンプル |

**重要**: ローカル cache が watchlist 相当のみの場合、出力は **scanner framework MVP** であり、全市場 discovery ではない。

---

## 6. Metrics and thresholds

| 定数 | 値 |
|---|---|
| `DISCOVERY_MIN_BARS` | 80 |
| `R5_RAPID` | ≥ 8% |
| `R20_RAPID` | ≥ 20% |
| `VOLUME_SPIKE_RATIO` | ≥ 2.0 |
| `NEAR_HIGH_DIST` | ≥ -5% |
| `OVERHEAT_R20` | ≥ 40% |
| `OVERHEAT_R60` | ≥ 80% |

`discovery_score`: breakout +2 · near_high +1 · volume_spike +2 · rapid_20d +2 · rapid_5d +1 · overheat -1

---

## 7. Output contract

- Markdown: テーブル + Candidate Groups + Next Research Checklist
- JSON: `universe_scope`, `candidates`, `safety`, `summary`
- 用語: deep-dive candidate · observation · overheat caution 等（docs/82 準拠）

---

## 8. Safety gates

- no trading recommendation · no cache write · no live HTTP by default
- low liquidity: `low_liquidity_caution` ラベル（avg25 volume 閾値）

---

## 9. Example commands

```bash
.venv/bin/python -m invis_alpha_os.cli.main discover-jp --format markdown --limit 20
.venv/bin/python -m invis_alpha_os.cli.main discover-jp --format json --limit 20
.venv/bin/python -m invis_alpha_os.cli.main discover-jp \
  --universe-file config/jp_universe_scanner_mvp.yaml --format markdown
```

---

## 10. Next phases

- **R7.0-C**: US Universe Scanner MVP
- **R7.0-D**: reputation/news layer
- **R7.0-E**: discovery daily report / Gmail

---

## 関連

- Planning: [docs/82](./82_r7_0_a_discovery_engine_planning.md)
- Codex prompt: `.agent/r7_0_a_discovery_engine_planning_codex_prompt.md`
