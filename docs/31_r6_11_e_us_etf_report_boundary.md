# R6.11-E — US equity / ETF policy and report staging（設計のみ）

**ステータス**: 作業ブランチ `work/r6-11-e-us-etf-report-boundary` のみ。**`main` 未反映**。本フェーズは **docs-only** — **実装なし**。

---

## 1. 目的

- R6.11-B/D の US signals 基盤から **report / portfolio / Veto** へ進む前に、**US equity / ETF** の扱いと **段階接続** を固定する
- **`debug us-cache-signals-preview`** と **daily report 節** の責務差を明確化する

## 2. R6.10〜R6.11 到達点（棚卸し）

| 層 | 成果 |
|----|------|
| Data | `us_daily_bars_cache` · envelope 検証 |
| Metrics | `compute_us_daily_bars_basic_metrics` · `debug us-daily-bars-cache-metrics` |
| Signals | `compute_us_cache_signal_row` · `debug us-cache-signals-preview` |
| Report（現状） | `render_us_momentum_cache_only_section` — **JP `build_momentum_signals` 経路のスケルトン**（非破壊維持） |

## 3. US equity / ETF 方針

### 3.1 当面の原則

- **US equity と US ETF は同一 cache パス**（`outputs/market_data/us_daily_bars/{SYMBOL}.json`）と **同一 signals helper**（`compute_us_cache_signal_row`）で扱う
- 種別は envelope / cache メタの **`asset_class`**（例: `us_equity` · `us_etf`）で区別し、**signals 計算ロジックは共通化**する
- R6.11-E では **ETF 固有スコア・レバレッジ調整・トラッキング誤差モデルは入れない**

### 3.2 watchlist 上の位置づけ（`config/us_watchlist.yaml`）

| 区分 | 例 | 役割 |
|------|-----|------|
| `us_equities` | MSFT, NVDA, … | 個別株モメンタム観測 |
| `us_etfs` | SPY, QQQ | **市場プロキシ** |
| `us_etfs` | GLDM, SLV | **メタル・コモディティプロキシ**（metals bridge・[docs/18](./18_r6_9_c_priority_us_metals_macro_portfolio.md) の metals 順位と整合） |
| `us_etfs` | TLT, TMF | 金利・デュレーション proxy（macro 接続の**前段**としてラベル分離のみ） |

### 3.3 `asset_class` / `asset_type`

- 既存: import CLI の **`asset_class`** 引数 · envelope 任意フィールド
- R6.11-F 候補: signals 行への **`asset_class` 伝播**を fixture で固定（実装は次フェーズ）
- **`asset_type`** という別名は導入せず、**`asset_class` に統一**（用語の二重化を避ける）

## 4. report 接続方針

### 4.1 段階

1. **現状（維持）**: `debug us-cache-signals-preview` で銘柄単位の JSON/Markdown 診断
2. **R6.11-G 候補**: report 用 **dry-run Markdown 節**の設計（ファイル出力のみ・daily report 本体は未接続）
3. **R6.12-A 候補**: 新節 `## US signals — cache only（us_cache_signals 経路）` を **フラグ付き**で追加（デフォルトは既存 `render_us_momentum_cache_only_section`）

### 4.2 CLI と report の違い

| 観点 | debug CLI | report 節（将来） |
|------|-----------|-------------------|
| 入力 | 単一 `--path` | watchlist 全銘柄 × cache 存在チェック |
| 出力 | 1銘柄の signal row | 表形式ランキング · スキップ理由列 |
| 契約 | `US_CACHE_SIGNAL_ROW_OK_KEYS` + `path` | 上記 + `skipped_no_cache` 等の列挙 |
| HTTP | **禁止** | **禁止** |

### 4.3 非破壊要件

- 既存 **`render_us_momentum_cache_only_section`** のデフォルト出力を変えない
- US signals 経路への差し替えは **設定フラグ**（例: `market_data.yaml`）が **明示 ON** のときのみ

## 5. Veto / portfolio / macro 接続前の安全ゲート

| ゲート | 内容 | 状態 |
|--------|------|------|
| G1 | `momentum_label` 契約固定 · golden 回帰 | R6.11-D まで部分完了 · R6.11-F で拡充候補 |
| G2 | equity / ETF ユニバース定義（watchlist + `asset_class`） | 本 doc で方針固定 |
| G3 | report 入力 JSON スキーマ合意 | 未着手（R6.11-G） |
| G4 | 閾値チューニング方針（観測ラベルのみ・売買指示なし） | 未着手 |
| G5 | 人間レビュー（ChatGPT / オペレータ） | 各 main 取り込み前 |
| G6 | VetoEngine 接続 | **R6.13+**（JP Veto ルールの US 転用は別設計） |
| G7 | portfolio allocation | [docs/18](./18_r6_9_c_priority_us_metals_macro_portfolio.md) 順位 **2** — signals/report 安定後 |
| G8 | macro regime | 順位 **3** — proxy ETF（TLT 等）はラベルのみ先行 |

## 6. R6.11-F 以降候補

| フェーズ | 内容 | cache-only |
|:--------:|------|:----------:|
| **R6.11-F** | US asset universe fixture · `asset_class` メタ docs | ✓ |
| **R6.11-G** | report section design · dry-run 出力仕様 | ✓ |
| **R6.11-H** | ETF 向け fixture 追加（SPY/GLDM 等）· golden | ✓ |
| **R6.12-A** | US signals report dry-run MVP（フラグ付き節） | ✓ |
| **R6.12-B** | portfolio allocation boundary docs | docs |
| **R6.13** | Veto 接続検討 | 要設計 |

## 7. 非目的

- 実装 · live HTTP · production cache write · API キー
- report 本体の本格接続 · Veto · portfolio · macro 本格接続
- JP momentum / Veto / daily report 既存挙動変更
- metrics / signals debug CLI 出力契約の破壊

## 8. 参照

- [docs/27_r6_11_a_us_signals_boundary_roadmap.md](./27_r6_11_a_us_signals_boundary_roadmap.md)
- [docs/30_r6_11_d_us_signals_debug_cli.md](./30_r6_11_d_us_signals_debug_cli.md)
- [docs/18_r6_9_c_priority_us_metals_macro_portfolio.md](./18_r6_9_c_priority_us_metals_macro_portfolio.md)
