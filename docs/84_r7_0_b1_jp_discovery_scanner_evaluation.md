# R7.0-B1 — JP Discovery Scanner Evaluation

**日付**: 2026-05-20 · **main**: `7891b3b` · **性質**: read-only evaluation · docs-only

---

## 1. Purpose

R7.0-B マージ後の `discover-jp` について、**有用性**と **universe/cache の広さ**を初回評価し、次の R7 ステップを決める。

---

## 2. Current Universe Breadth

| 指標 | 値 |
|---|---|
| JP cache JSON 数 | **11** |
| cache 銘柄（wire） | 285A, 5411, 5801, 5802, 5803, 6501, 6504, 6506, 7011, 7203, 7267 |
| `config/jp_universe_scanner_mvp.yaml` | **3** 銘柄（7011, 7203, 6501） |
| 性質 | **watchlist 相当** — 全市場横断ではない |

---

## 3. Output Summary

### Run A — `local_cache_available_symbols`（cache 全件 · limit 20）

| 項目 | 値 |
|---|---|
| universe_scope | `local_cache_available_symbols` |
| symbols scanned | 11 |
| ranked candidates | 11 |
| insufficient | 0 |
| data_quality | 全件 `ok` |

**Top candidates（discovery_score）**

| rank | code/name | score | labels |
|---:|---|---:|---|
| 1 | 5802 | 3 | near_high, rapid_mover_20d |
| 2 | 5801 | 2 | rapid_mover_20d, rapid_mover_5d, overheat_caution |
| 3 | 285A | 2 | rapid_mover_20d, rapid_mover_5d, overheat_caution |

**Label counts（ranked set）**: near_high 2 · rapid_mover_20d 4 · rapid_mover_5d 2 · overheat_caution 2

### Run B — `sample_jp_universe`（YAML 3 銘柄）

| 項目 | 値 |
|---|---|
| universe_scope | `sample_jp_universe` |
| ranked | 3 · insufficient 0 |
| top | 7011 三菱重工（score 1, near_high）· 7203/6501 score 0 |

---

## 4. Evaluation

### useful_for

- scanner framework 検証（CLI · markdown/json · display names · ラベル付け）
- **利用可能 cache 内**の follow-up 候補の並び替え
- observation-only 契約の維持（禁止語なし）

### not_yet_useful_for

- **full-market JP discovery**（cache が 11 銘柄のみ）
- reputation / narrative 検出（R7.0-D 待ち）
- 広いセクター横断の網羅的スクリーニング

### noisy / caveats

- ユニバースが狭いため、ラベルは **既知 watchlist の相対比較**に近い
- breakout / volume_spike は cache 次第で出現が偏る可能性
- insufficient-data は今回 **0%**（min_bars 未満の銘柄は cache に未登録のため）

---

## 5. Recommendation

**Option C — R7.0-B2 JP cache/universe expansion**（推奨）

理由:

- スキャナー本体は動作し、11 銘柄では **意味のあるラベル分化**（5802 near_high+rapid 等）が見える
- ただし universe は明らかに **狭すぎる**（watchlist 拡張が先）
- insufficient-data 支配ではないため、Option A 単独より **breadth 拡張 Longpack（B2）** が適切

代替:

- **Option B（R7.0-C US MVP）** — JP breadth を後回しにし US 対称性を優先する場合は可能。ただし JP 側の運用価値は cache 拡張後に再評価推奨。

---

## 6. Safety

- evaluation は read-only · no live HTTP · no cache write
- no trading recommendation · no default enablement
- ローカル出力: `outputs/operator/discovery_eval/2026-05-20/`（gitignore）

---

## 7. Next Action

1. **R7.0-B2 Longpack**: JP cache/universe 拡張（listed subset または watchlist+α の明示 YAML）
2. 拡張後に `discover-jp` を再評価（B1 手順の繰り返し）
3. JP breadth が十分になったら **R7.0-C US Scanner MVP** へ

---

## 関連

- 実装: [docs/83](./83_r7_0_b_jp_universe_scanner_mvp.md)
- Planning: [docs/82](./82_r7_0_a_discovery_engine_planning.md)
- ローカルサマリー: `outputs/operator/discovery_eval/2026-05-20/discover_jp_eval_summary.json`
