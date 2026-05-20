# R7.0-B4 — JP Discovery Re-evaluation（Core50 40/50 到達後）

**日付**: 2026-05-20 · **main 起点**: `bca1ee9` · **性質**: read-only 再評価 · docs-only PR

**先行**: R7.0-B3S2 証跡 [docs/94](./94_r7_0_b3s2_core50_cache_fill_evidence.md)

---

## 1. Purpose

Core50 キャッシュ検証 **≥40/50** を満たした前提で、`discover-jp` の実用性と次工程（**R7.0-C US MVP** vs **JP 継続拡張**）の判断材料を整理する。

---

## 2. Core50 coverage（再確認 · read-only）

| 項目 | 値 |
|---|---:|
| universe | `config/jp_universe_core50.yaml` |
| total | 50 |
| **ok**（bars ≥ **80**） | **40** |
| **missing** | **10** |
| sufficient bars 条件 | **80** bars（J-Quants OHLCV の観測用しきい値） |

**missing（10）**: ローカル `outputs/operator/discovery_eval/2026-05-20/r7_0_b4/coverage_summary.json` 参照（コミットしない）。

**方法**: `load_jquants_daily_bars_cache` · **live HTTP / cache write なし**

---

## 3. `discover-jp` 再実行（Core50）

**コマンド**:

```bash
.venv/bin/python -m invis_alpha_os.cli.main discover-jp \
  --universe-file config/jp_universe_core50.yaml --format json

.venv/bin/python -m invis_alpha_os.cli.main discover-jp \
  --universe-file config/jp_universe_core50.yaml --format markdown --limit 25
```

**証跡（ローカル・未コミット）**:

- `outputs/operator/discovery_eval/2026-05-20/r7_0_b4/discover_jp_core50.json`
- `outputs/operator/discovery_eval/2026-05-20/r7_0_b4/discover_jp_core50.md`

### 3.1 Summary（JSON `summary`）

| 指標 | 値 |
|---|---:|
| symbol_count | 50 |
| **ranked_candidate_count** | **20** |
| **insufficient_count** | **10** |

`insufficient_count` は coverage の missing（10）と一致（cache 不足でランキング対象外）。

### 3.2 上位候補（スコア順 · 抜粋）

| # | code/name | discovery_score | labels（抜粋） |
|---:|---|---:|---|
| 1 | 5802 住友電工 | 3 | near_high, rapid_mover_20d |
| 2 | 6645 オムロン | 3 | near_high, rapid_mover_20d |
| 3 | 5801 古河電工 | 2 | rapid_mover_20d, rapid_mover_5d, overheat_caution |
| 4 | 5803 フジクラ | 2 | rapid_mover_20d |
| 5 | 6857 アドバンテスト | 2 | rapid_mover_20d |

（全件は上記 JSON を参照）

### 3.3 ラベル分布（ranked 20 件における出現回数）

| label | count |
|---|---:|
| near_high | 12 |
| rapid_mover_20d | 5 |
| rapid_mover_5d | 2 |
| overheat_caution | 1 |

**所見（観測）**: 当回ランキングでは **near_high が主流**。**high_52w_breakout** は本ランク集合では目立たず、銘柄セットと期間に依存。volume 系ラベルも今回の上位集合では限定的。

### 3.4 読みやすさ・Gmail 統合

| 観点 | 評価 |
|---|---|
| CLI JSON | `summary` と `candidates[]` で自動集計しやすい |
| Markdown (`--limit`) | 人間向け短表に寄せやすい |
| 日本語 Gmail | R6.19-G の「今日の注目」「銘柄別コメント」へ **要約文＋上位ラベル**を差し込める（**観測の補強**であり売買提案ではない） |
| 限界 | ranked は **cache あり銘柄の部分集合**（40/50 のうちランク入り 20）· 残 10 は説明用に「データ不足」セクションが必要 |

---

## 4. B1 / B3S 前 / B3S2 後 の比較

| 時点 | coverage（観測） | discover 観測 | 評価メモ |
|---|---|---|---|
| **B1**（[docs/84](./84_r7_0_b1_jp_discovery_scanner_evaluation.md)） | cache **11** 銘柄規模 | ranked **11** · universe 狭い | framework 検証向き · 全市場ではない |
| **B3S 前**（R7.0-B3S 時点） | Core50 **30/50** | ranked **20** · insufficient 増 | Core50 形に近づくが目標 40 未満 |
| **B3S2 後**（本記録） | Core50 **40/50** | ranked **20** · insufficient **10** | **事前合意しきい値 ≥40 を満たす** · なお ranked 上限は実装/銘柄フィルタにより 20 前後 |

---

## 5. 判断表（R7.0-C vs JP 拡張）

| 判断軸 | R7.0-C US MVP へ進む | JP 拡張を続ける |
|---|---|---|
| **開発価値** | US 側の観測・レポート一貫性を先に固め、JP/US 二系統の **product 面**を揃えやすい | Core50 を **50/50** または **JP100** に広げると discover の母集団・ラベル多様性が増す |
| **discovery engine 完成度** | JP は **≥40 到達**により合意ゲートをクリア。ランキングロジック自体は cache 母集団に依存する点は残る | remaining **10** と universe 拡大は **insufficient の圧縮**に直結 |
| **データ取得リスク** | US は cache read 中心の MVP なら JP live 追加と切り離せる | JP 追加 ingest は **明示ゲート live + write**（レート制限リスク） |
| **実用レポート価値** | Gmail 日本語ナラティブは既存。US 節を増やす場合は **別 cache 前提**が明確でよい | JP 表の欠損銘柄が減り、**銘柄一覧の説明負荷**が下がる |
| **次のボトルネック** | US universe 定義 · US cache 運用 · メール節の情報設計 | JP **10** の埋め合わせ · さらなる universe YAML 設計 |

---

## 6. 推奨結論（データに基づく）

**採用: 案 A — R7.0-C US Universe Scanner MVP へ進む**

**根拠**:

1. Core50 **40/50（≥80 bars）** は、従来の **R7.0-C 進行前提**（JP 側の最低カバレッジ）を満たす。
2. `discover-jp` は ranked **20** · ラベル **near_high / rapid_mover / overheat_caution** で **観測向けの並び替え**として運用可能。
3. 残 **10/50** は discover の `insufficient_count` と整合し、**JP 埋め合わせは R7.0-C と並行の低リスク・小バッチ**で継続できる（B3S2 型のゲートを維持）。

**案 B**（JP を最優先で 50/50 または JP100）: レポートの **JP 完全性**を最優先する場合に選択。

**案 C**（US MVP と JP 拡張並行 + runner 先行）: **R7.0-Ops-A** 運用を最優先する場合。本ドキュメントは evidence のみ; Ops Longpack 到着後に再優先度付けしてよい。

---

## 7. Safety

- live HTTP / cache write: **未実施**
- secrets / `.env`: **未出力**
- cache JSON / `outputs/`: **未コミット**
- 売買推奨・銘柄推奨: **記載しない**（観測・スコア並び替えの説明のみ）

---

## 8. 関連

- [docs/94](./94_r7_0_b3s2_core50_cache_fill_evidence.md) · [docs/88](./88_r7_0_b3s_jp_core50_cache_fill_continuation.md) · [docs/84](./84_r7_0_b1_jp_discovery_scanner_evaluation.md)
