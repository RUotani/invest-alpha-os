# R7.0-B2 — JP Universe / Cache Expansion

**日付**: 2026-05-20 · **main**: `5e36345`+ · **性質**: universe/config expansion + coverage audit

---

## 1. Purpose

R7.0-B1 の推奨に従い、JP discovery を watchlist 相当（11 cache）から **Core50 キュレーション universe** へ拡張し、cache カバレッジを可視化する。

---

## 2. Starting point (R7.0-B1)

| 指標 | 値 |
|---|---|
| JP cache files | 11 |
| YAML sample | 3 |
| discover-jp ranked (cache) | 11 |
| 判定 | フレームワーク OK · **breadth 不足** |

---

## 3. Core50 universe config

- ファイル: `config/jp_universe_core50.yaml`
- `universe_scope`: `curated_liquid_cross_sector_sample`
- 銘柄数: **50**（流動性・セクター横断のサンプル）
- **not** full-market discovery

---

## 4. Universe scope caveat

Core50 は東証全市場ではない。`discover-jp` は各銘柄について **ローカル cache があれば metrics を計算**し、無ければ `insufficient` / `invalid_bars` として記録する（live HTTP は行わない）。

---

## 5. Cache coverage (2026-05-20 audit)

| 指標 | 値 |
|---|---|
| Core50 symbols | 50 |
| JP cache files (local) | 11 |
| Cache hit in Core50 | **9** |
| Ranked `ok` | **9** |
| Missing / insufficient | **41** |

**Top ranked（cache あり）**: 5802 (score 3) · 5801 / 5803 (score 2) · 7011 (near_high)

---

## 6. Optional ingest

**Skipped** — 既存 gated path は `debug jquants-daily-bars-cache --live --write-cache` + `CONFIRM_LIVE_HTTP=YES`（J-Quants 三重ゲート）。本 Longpack では **live HTTP / cache write 未実行**。

**Next**: **R7.0-B3** — JP ingest/cache 標準化（バッチ ≤10 · 明示ゲート · カバレッジ再監査）。

---

## 7. Discover-jp after expansion

```bash
.venv/bin/python -m invis_alpha_os.cli.main discover-jp \
  --universe-file config/jp_universe_core50.yaml --format markdown --limit 30
```

- `universe_scope` が `curated_liquid_cross_sector_sample` と明示される
- display names: `config/symbol_display_names.yaml` 更新済み

---

## 8. Remaining blockers

- **41/50** 銘柄に cache 未整備 → 横断 discovery としてはまだ狭い
- reputation/news 層なし（R7.0-D）
- 9984 等、cache wire 制約で将来 ingest 時に要確認

---

## 9. Recommendation

1. **R7.0-B3**: gated JP cache fill（Core50 の missing 分をバッチ ingest）
2. B3 後に B1 手順で再評価（目安: ranked ok ≥ 40/50）
3. JP breadth が実用域に入ってから **R7.0-C US MVP**

---

## 関連

- [docs/84](./84_r7_0_b1_jp_discovery_scanner_evaluation.md)
- [docs/83](./83_r7_0_b_jp_universe_scanner_mvp.md)
- ローカル: `outputs/operator/discovery_eval/2026-05-20/r7_0_b2/`
