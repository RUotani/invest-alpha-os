# R6.11-A — US signals boundary / roadmap（設計のみ）

**ステータス**: **main 反映済み**（`92d0a10`）。branch CI `25920084716` — success。本フェーズは **docs / design** — **US signals 本実装は R6.11-B 以降**。

---

## 1. 目的

- **R6.10-A〜H** で整えた US cache-only **data / validation / preview / metrics** 基盤から、**US signals MVP** へ進む前に **責務境界・入力・出力・非目的** を固定する。
- **cache-only**（live HTTP なし）でテスト可能な **R6.11-B 以降** のタスクを切り出す。

## 2. 非目的（R6.11-A 全体）

- live HTTP / production cache write / `.env` / API キー
- US signals **本実装**（本ドキュメントは境界整理のみ）
- **VetoEngine** / **daily report** 本格接続 / **portfolio** / **macro regime** 本格接続
- JP momentum / Veto / daily report の既存挙動変更
- R6.10 metrics **計算仕様**・**metrics command 出力契約**の破壊

---

## 3. R6.10-A〜H で完成したもの（棚卸し）

| フェーズ | 成果 | 主な API / CLI |
|--------|------|----------------|
| **A** | cache-only reader MVP | `parse_us_daily_bars_payload`, `load_us_daily_bars_json_file` |
| **B** | validation / fixture 強化 | 同上 + 回帰テスト |
| **C** | preview diagnostics | `build_us_daily_bars_cache_preview`, `debug us-daily-bars-cache-preview` |
| **D** | preview 出力契約 | `PREVIEW_OK_KEYS`, `PREVIEW_INVALID_BASE_KEYS` |
| **E** | basic metrics（pure） | `compute_us_daily_bars_basic_metrics` |
| **F** | metrics diagnostics CLI | `build_us_daily_bars_cache_metrics_preview`, `debug us-daily-bars-cache-metrics` |
| **G** | metrics CLI hardening | `METRICS_PREVIEW_INVALID_BASE_KEYS`, 異常系テスト |
| **H** | 実用 fixture + golden 回帰 | `msft_25bars_metrics_envelope.json`, JSON/Markdown golden tests |

**共通制約**: すべて **cache-only** · **no live HTTP** · **no production cache write**（診断・テスト用）。

---

## 4. レイヤー境界（推奨）

```text
[fixture / outputs/market_data/us_daily_bars/*.json]
        ↓
  us_daily_bars_cache     ← R6.10-A/B（読込・検証）
        ↓
  us_daily_bars_metrics   ← R6.10-E（指標計算・診断用）
        ↓
  (新) us_signals         ← R6.11-B 以降（シグナル判定・ランキング行）
        ↓
  CLI debug / report 節  ← R6.11-D / 将来
        ↓
  VetoEngine / portfolio  ← R6.12+（別判断・本タスク外）
```

| 層 | 責務 | 今回まで | 次段階 |
|----|------|----------|--------|
| **Data** | envelope 検証・`DailyBar[]` | R6.10-A/B | 変更最小 |
| **Metrics** | `total_return`, `return_5d`, `return_20d`, `has_*` | R6.10-E〜H | signals から **読むだけ**（再実装しない） |
| **Signals** | 銘柄ごとの観測行・ランキング用スコア候補 | **未整備** | R6.11-B MVP |
| **Report** | Markdown 節 | `render_us_momentum_cache_only_section`（JP `build_momentum_signals` 再利用） | 契約固定後に段階接続 |

**重要**: 既存 **`render_us_momentum_cache_only_section`**（`reports/momentum_daily.py`）は JP と同じ **`build_momentum_signals`** 経路を使う **スケルトン**。R6.11 では **US 専用の薄い signals 層**を挟み、将来的に **score_v2 閾値の US 調整**や **metrics 連携**を検討するが、**当面は非破壊**（既存節は壊さない）。

---

## 5. US signals MVP の候補入力

**R6.11-B で想定する最小入力**（いずれも cache-only で fixture 化可能）:

| 入力 | 出所 | 備考 |
|------|------|------|
| `bars: list[DailyBar]` | `load_us_daily_bars_json_file` | 必須・昇順 |
| `symbol` | envelope meta | 表示・キー |
| `bar_count`, `first_date`, `last_date` | metrics または bars | 期間ゲート |
| `total_return`, `return_5d`, `return_20d` | `compute_us_daily_bars_basic_metrics` | **再利用**（再計算は避ける） |
| `has_5d`, `has_20d` | 同上 | insufficient bars の明示 |
| `last_close`, `last_volume` | 同上 / 直近 bar | 参考表示 |

**次段階候補**（R6.11-C 以降）:

- volume spike / `volume_ratio`（JP `detect_volume_spike` 相当の US 閾値検討）
- drawdown / volatility / breakout（JP score_v2 部品の選別移植）
- US ETF 用の **流動性・トラッキング誤差**フラグ（データが揃ってから）

---

## 6. US signals MVP の候補出力（契約たたき台）

**R6.11-B で固定したい最小 JSON 行イメージ**（名前は実装時に確定）:

- `symbol`, `status` (`ok` | `skipped_insufficient_bars` | `invalid`)
- `return_5d`, `return_20d`, `total_return`（nullable）
- `signal_tier` または `momentum_label`（観測用ラベル・**売買指示ではない**）
- `live_http: false`, `source: cache_only`

**非目標**: broker 注文・ポジションサイズ・Veto レベル（別エンジン）。

---

## 7. JP momentum subsystem との比較

| 観点 | JP（現状） | US（R6.11 方針） |
|------|------------|------------------|
| バー読込 | J-Quants cache / synthetic | **US envelope** + `us_daily_bars_cache` |
| コア計算 | `signals/momentum.py`（`calculate_returns`, score_v2） | まず **metrics 再利用** + 薄い **US signals helper** |
| CLI | `signals`（JP 中心） | 既存はそのまま · **新規は `debug us-signals-cache-preview` 類**を R6.11-D で検討 |
| daily report | `render_momentum_signals_*` | `render_us_momentum_cache_only_section` 維持 · 内部実装差し替えは **後続** |
| Veto | `VetoEngine` + YAML | **接続前**に US signals 出力契約を固定 |

**流用してよい考え方**: 昇順 `DailyBar` · horizon return 定義 · cache-only テスト · ranked list の Markdown 表形式。

**そのまま流用しないもの**: JP 固有コード正規化 · J-Quants パス · score_v2 定数（US 用に別ファイルで再定義検討）。

---

## 8. US equities と US ETF の境界

- **データパス**: 同一 `outputs/market_data/us_daily_bars/{SYMBOL}.json`（既存 watchlist で `us_equity` / `us_etf` 区分）。
- **R6.11-B**: **同一 signals helper** で envelope を処理（symbol 種別は **メタデータラベル**のみ）。
- **R6.11-E（候補）**: ETF 専用の **除外ルール・注記**（レバレッジ ETF 等）は **ポリシー docs** で整理し、実装は最小。

---

## 9. 接続順序（推奨ロードマップ）

| 順 | フェーズ | 内容 | cache-only |
|:--:|--------|------|:----------:|
| 1 | **R6.11-B** | `us_signals` pure helper MVP（bars + metrics → 行 dict） | ✓ |
| 2 | **R6.11-C** | fixture / golden-style regression | ✓ |
| 3 | **R6.11-D** | `debug us-signals-cache-preview`（metrics CLI と同型の診断入口） | ✓ |
| 4 | **R6.11-E** | US ETF ポリシー・watchlist 注記 docs | ✓ |
| 5 | **R6.12** | daily report 節の **オプション差し替え**（フラグ付き・デフォルト旧挙動） | ✓ |
| 6 | **R6.13+** | Veto 接続検討（US ルール YAML · 閾値） | 要設計 |
| 7 | **以降** | portfolio / macro（[docs/18](./18_r6_9_c_priority_us_metals_macro_portfolio.md) の順位尊重） | 別ライン |

---

## 10. R6.11-B 以降の受け入れ条件（たたき台）

- focused pytest 全緑 · full pytest 全緑 · branch CI success
- **no live HTTP** · **no production cache write**
- metrics / preview CLI の **既存 golden 非破壊**
- 新規テストは **fixture のみ**

---

## 11. 参照

- R6.10 系: `docs/19_r6_10_a_*` 〜 `docs/26_r6_10_h_*`
- 優先順位: [docs/18_r6_9_c_priority_us_metals_macro_portfolio.md](./18_r6_9_c_priority_us_metals_macro_portfolio.md)
- 実装アンカー: `src/invis_alpha_os/data/us_daily_bars_cache.py`, `us_daily_bars_metrics.py`, `signals/momentum.py`, `reports/momentum_daily.py`
