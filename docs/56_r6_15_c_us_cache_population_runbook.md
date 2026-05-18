# R6.15-C — US daily bars cache population runbook

**ステータス**: **完了・`main` 反映済み**（PR **#3** · `f6250d8`）。本書は運用 runbook。

本書は **実データ取得コードの追加**ではなく、US signals / daily report を **cache-only** で運用する前に、オペレータが **何を確認し・どこまで手動でできるか**を固定する **runbook（docs-only）** である。

---

## 1. 目的

- **現状の US cache-only 構成**（パス・JSON envelope・watchlist）を一文で辿れるようにする。
- **watchlist 全銘柄**を `outputs/market_data/us_daily_bars/` に載せる **前**のチェックリストを定義する。
- **live HTTP** および **production cache write** を **まだ本番運用で有効化しない**前提を明記する。
- **R6.16 / R6.17** で実装すべき境界（自動 ingest・daily 接続）を切り出す。

## 2. 非目的（本タスク / 本書の範囲外）

- **yfinance / Stooq / J-Quants 等の新規取得クライアント**の実装。
- **watchlist 一括の無人 cache refresh**（cron / Actions / Makefile 拡張）。
- **`include_us_momentum_cache_only_section` の default を `true` にする**変更。
- **US signals の本番接続**・**Veto / portfolio / macro** 接続。
- **`.github/workflows/*`** の変更。

---

## 3. 現状の US cache-only 構成

| 層 | 内容 |
|---|---|
| **設定** | `config/us_watchlist.yaml` — `us_equities` / `us_etfs` / `crypto_proxy`（順序保持・重複は先勝ち） |
| **on-disk cache** | `outputs/market_data/us_daily_bars/{SYMBOL}.json`（**Git 管理外** · `.gitignore`） |
| **読み取り** | `us_daily_bars_cache.try_load_cached_us_daily_bars` · `parse_us_daily_bars_payload` |
| **momentum / daily** | `render_us_momentum_cache_only_section` — **`config/market_data.yaml` の `include_us_momentum_cache_only_section: false` が default**（US ブロックは daily に出ない） |
| **CI / ローカル最小例** | `make us-cache-fixture-import` → **MSFT / GOOGL / GLDM の 3 銘柄のみ** `outputs/` へコピー相当 |
| **検証スクリプト** | `make us-momentum-check`（3 ファイルが無ければ fixture import を試行） |

**観測のみ**: cache が無い銘柄は **skipped** 扱い。US セクションを daily に出しても **空に近い表示**になり得る（[review_integrated_20260515.md](./review_integrated_20260515.md) の HIGH 指摘と整合）。

---

## 4. JSON envelope（1 ファイル = 1 銘柄）

**パス**: `outputs/market_data/us_daily_bars/{SYMBOL}.json`（`SYMBOL` は `normalize_us_symbol` 後の slug、例: `MSFT`）。

**ルートキー**（`schema_version` **= 1** のみ許可）:

| キー | 必須 | 説明 |
|---|---|---|
| `schema_version` | yes | 整数 **`1`** |
| `symbol` | yes | 正規化済みティッカー |
| `bars` | yes | OHLCV 行の配列（下記） |
| `bar_count` | 推奨 | `len(bars)` と一致 |
| `source` | 推奨 | 例: `local_fixture` · `stooq`（**secret 様文字列禁止**） |
| `asset_class` | 任意 | 例: `us_equity` · `us_etf` |
| `fetched_at` / `generated_at` | 任意 | ISO 時刻（UTC 生成は `save_us_daily_bars_cache` が付与可） |

**`bars[]` 各行**: `date`（`YYYY-MM-DD`）· `open` · `high` · `low` · `close` · `volume` — **日付は昇順・重複なし**。

**禁止**: `raw_response` · `api_key` · vendor 生 CSV 全文など（`save_us_daily_bars_cache` / `parse_us_daily_bars_payload` が拒否）。

**fixture との違い**: `tests/fixtures/us_daily_bars/*.json` は **行配列のみ**（envelope なし）。cache へ入れるときは **`debug us-daily-bars-cache-import`** が envelope を付けて書く。

---

## 5. watchlist 全銘柄を載せる前の確認手順（runbook）

### 5.1 インベントリ

```bash
cd /Users/uotani/Projects/invest-alpha-os
PYTHON=.venv/bin/python -m invis_alpha_os.cli.main us-watchlist-preview
ls -1 outputs/market_data/us_daily_bars/*.json 2>/dev/null | wc -l
```

- **期待**: watchlist 件数 ≫ 現状 cache ファイル数（多くの環境で **0〜3**）。

### 5.2 既存の安全な投入手段（コード変更なし）

| 手段 | HTTP | cache write | 用途 |
|---|---|---|---|
| `make us-cache-fixture-import` | なし | **あり**（3 銘柄・fixture） | ローカル / CI 向け最小セット |
| `debug us-daily-bars-cache-import --symbol SYM --bars-file PATH [--write-cache]` | なし | **`--write-cache` 時のみ** | 手元 CSV/JSON 配列から 1 銘柄 |
| `make us-provider-cache-preview-dry-run` / `debug us-provider-cache-preview`（**`--live` なし**） | なし | なし | 形状・ゲート確認 |
| `make us-provider-cache-preview-batch-dry-run` | なし | **batch は `--write-cache` 拒否** | watchlist 複数銘柄の **dry-run 集計** |
| `make us-provider-cache-write-stooq`（要 `CONFIRM_US_CACHE_WRITE=YES`） | **あり** | **1 銘柄・全ゲート** | **オペレータ明示のみ** — 本 runbook では **本番一括の前提にしない** |

**本 runbook の立場**: 全 watchlist を埋める作業は **手順の整理まで**。一括 live ingest は **R6.16 以降**。

### 5.3 投入前チェックリスト（銘柄あたり）

- [ ] `normalize_us_symbol` が通る（`config/us_watchlist.yaml` の表記と一致）
- [ ] `bars` が非空・日付昇順
- [ ] `schema_version: 1` · 余剰キーなし
- [ ] `source` に secret 様文字列が無い
- [ ] **dry-run** でパスを確認: `debug us-daily-bars-cache-import ...`（**`--write-cache` なし**）→ `cache_would_write_to` を確認
- [ ] 書き込み後: `try_load_cached_us_daily_bars` 相当が通る（`make us-momentum-check` または該当 symbol の pytest fixture パターン）

### 5.4 書き込み後のリポジトリ衛生

- `outputs/market_data/us_daily_bars/*.json` は **コミットしない**（`.gitignore`）。
- **誤って `git add outputs/` しない**（`make main-gate` / pre-commit の forbidden-paths 参照）。

---

## 6. live HTTP / production cache write — まだ有効化しない前提

| 項目 | 現状 |
|---|---|
| **daily US セクション** | **default off**（`include_us_momentum_cache_only_section: false`） |
| **Stooq live** | `CONFIRM_US_LIVE_HTTP=YES` + CLI `--live` + その他ゲート（[docs/11_us_market_data_provider_plan.md](./11_us_market_data_provider_plan.md)） |
| **production cache write** | `CONFIRM_US_CACHE_WRITE=YES` + `--write-cache` / `--execute-cache-write` 等（[docs/15_us_provider_manual_cache_write_evaluation_design.md](./15_us_provider_manual_cache_write_evaluation_design.md)） |
| **無人スケジュール** | [docs/13_us_provider_scheduled_ingest_design.md](./13_us_provider_scheduled_ingest_design.md) — **設計のみ** |

**オペレータ向け原則**: 本フェーズでは **fixture 3 銘柄 + dry-run プレビュー**までを標準とし、**watchlist 全件の live 一括取得は行わない**。

---

## 7. 将来境界 — R6.16 / R6.17（案）

| ID | 想定スコープ | 本書との関係 |
|---|---|---|
| **R6.16** | **Operator-gated バッチ ingest**（watchlist 単位・上限付き live HTTP · 監査ログ · 失敗行列は [docs/12](./12_us_provider_failure_operator_playbook.md)） | **取得実装の最小実行面** — 本 runbook §5.2 の「一括」をコード化 |
| **R6.17** | **daily / signals への US cache-only 接続判断**（cache 充足率しきい値 · `include_us_momentum_cache_only_section` は **別承認で default 変更可**） | **表示・意思決定支援** — cache が無い銘柄の UX |

**R6.15-C では上記を実装しない**。docs とチェックリストのみ。

### 7.1 R6.16-A 着手 entry criteria（read-only 棚卸しまで）

- **ruleset `main` active** · required check **`test`** · **main CI green**
- **cache inventory は read-only**（live HTTP なし · production cache write なし）
- **US default report / `include_us_momentum_cache_only_section` default 変更なし**
- **Veto / portfolio / macro 接続なし**

---

## 8. 関連ドキュメント

- [docs/11_us_market_data_provider_plan.md](./11_us_market_data_provider_plan.md)
- [docs/12_us_provider_failure_operator_playbook.md](./12_us_provider_failure_operator_playbook.md)
- [docs/15_us_provider_manual_cache_write_evaluation_design.md](./15_us_provider_manual_cache_write_evaluation_design.md)
- [docs/19_r6_10_a_us_equities_cache_only_mvp.md](./19_r6_10_a_us_equities_cache_only_mvp.md)
- [docs/review_integrated_20260515.md](./review_integrated_20260515.md)

## 9. 次候補

- **R6.16**: operator-gated US cache batch ingest（**別承認・実装タスク**）。
- **R6.17**: US cache 充足後の daily / signals 接続判断（**別承認**）。
- **R6.14-J**: R12 worktree cleanup 継続（**別承認**）。
