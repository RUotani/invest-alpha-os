# R6.16-C — Operator-gated US cache ingest（design only）

**ステータス**: **design docs · `main` 反映済み**（PR **#9** · `45b3796`）。**ingest plan CLI 実装は別承認**。  
**運用結果**: 手動 gated single-symbol ingest により watchlist **ok 16 / missing 0**（2026-05-19）— **[docs/62](./62_r6_16_d_us_cache_full_population_status.md)**。

---

## 1. 背景 — real cache inventory smoke（2026-05-19 · `main` @ `a34562f` 付近）

`debug us-daily-bars-cache-inventory --cache-root outputs/market_data/us_daily_bars`（read-only）:

| 指標 | 値 |
|---|---|
| total_symbols | 16 |
| ok | 3（MSFT · GOOGL · GLDM） |
| missing | 13 |
| invalid | 0 |
| insufficient | 0 |
| stale_unknown | 0 |

**含意**: ingest 対象は原則 **missing のみ**。既存 **ok** 3 銘柄は **無断上書きしない**（明示 opt-in がない限りスキップ）。

---

## 2. 目的 / 非目的

### 目的

- [docs/56](./56_r6_15_c_us_cache_population_runbook.md) §7 の **operator-gated バッチ ingest** を、実装前に **ゲート・上限・失敗処理・検証手順**として固定する。
- 既存 CLI（`us-provider-cache-preview-batch` · `us-provider-manual-live-batch-smoke` · 単銘柄 `us-provider-cache-preview`）の **dry-run 既定**と整合させる。

### 非目的（R6.16-C 実装タスクでも禁止）

- live HTTP / production cache write の **無人・default 有効化**
- yfinance / stooq / J-Quants 等の **新規取得アダプタ追加**（既存 Stooq 経路のラップのみ想定）
- US signals / daily report **default 変更** · Veto / portfolio / macro 接続
- workflow / Makefile / pyproject 変更（実装 PR でも **別判断**）

---

## 3. 用語 — inventory `ok` と `fresh enough` の分離

| 概念 | 定義 | inventory 上の目安 |
|---|---|---|
| **`ok`（cache_valid）** | ファイル存在 · JSON 検証通過 · bar 数 ≥ 最小（現状 5）· **`fetched_at` または `generated_at` が非空** | `status=ok` · `reason=ok` |
| **`fresh enough`（運用鮮度）** | 最終 bar 日付（またはメタデータ日付）が **オペレータ定義のしきい値**以内 | **inventory では未判定**（R6.16-C 実装で別フィールド `freshness_status` 等を検討） |

**設計原則**: 現状 smoke の MSFT/GOOGL/GLDM は **`ok` だが last_date は 2024 年止まり** → **signals 用途には不十分な可能性**がある。ingest 計画では **`ok` を自動スキップ**し、鮮度不足は **R6.16-C 実装後の拡張**または **手動「refresh 承認リスト」**で扱う（default では refresh しない）。

---

## 4. 実行モード — dry-run default

| モード | HTTP | cache write | 既定 |
|---|---|---|---|
| **plan / dry-run** | なし | なし | **✅ default** |
| **live preview** | あり（ゲート済） | なし | 明示のみ |
| **cache write** | あり（ゲート済） | あり | 明示のみ · **単銘柄** |

- バッチエントリは **`debug us-provider-cache-preview-batch`（dry-run）** または将来の **`…-ingest-plan`** 相当から開始。
- **batch エンベロープからの一括 write は拒否**（既存: `batch_cache_write_not_supported`）— R6.16-C も同じ。

---

## 5. 二重ゲート

### 5.1 live HTTP

1. **環境**: `CONFIRM_US_LIVE_HTTP=YES`（シェル export · 子プロセスのみ有効化を推奨）
2. **CLI**: `--live`（または `--execute-live-http` 系の明示サブコマンド）

参照: [docs/11](./11_us_market_data_provider_plan.md) · `debug us-provider-live-preview` · `us-provider-manual-live-batch-smoke`（R6.4.1）。

### 5.2 production cache write

1. **環境**: `CONFIRM_US_CACHE_WRITE=YES`
2. **CLI**: `--write-cache` / `--execute-cache-write`（単銘柄 · 評価 dry-run 後）

参照: [docs/15](./15_us_provider_manual_cache_write_evaluation_design.md) · 単銘柄 `debug us-provider-cache-preview`。

**R6.16-C 実装時**: 両ゲートが揃わない限り **HTTP も write も行わない**（exit ≠ 0 または `validation_error` 行で記録）。

---

## 6. missing-only ingest

### 6.1 対象選定

1. **before**: `debug us-daily-bars-cache-inventory` で JSON `summary` を保存（ローカル · **Git 管理外**）
2. **対象**: `status=missing` · `reason=missing_file` の symbol のみ
3. **除外**: `ok` · `insufficient` · `invalid` · `stale_unknown`（鮮度 refresh は **別リスト・別承認**）

### 6.2 smoke 時点の missing 13（参考）

NVDA · AAPL · AMZN · META · TSLA · SLV · TLT · TMF · SPY · QQQ · MSTR · COIN · MARA

**運用**: 初回実装後も **全 13 を一括しない**。§7 の batch 上限に従い段階投入。

---

## 7. batch 上限（提案初期値 — 実装 PR で確定可）

| 上限 | 提案 | 理由 |
|---|---|---|
| **max_symbols_per_run** | **3** | 既存 fixture 3 銘柄文化 · smoke で ok が 3 |
| **max_http_attempts_per_run** | **3** | `us-provider-manual-live-batch-smoke` の `--max-http` 文化と整合 |
| **max_cache_writes_per_run** | **1** | 単銘柄 write 徹底 · 失敗時の切り分け容易 |
| **cooldown** | 手動（次 run は別ターミナルセッション） | 無人スケジュール禁止 |

超過時: **計画段階で拒否**（dry-run summary に `rejected_over_cap`）— HTTP/write 前。

---

## 8. symbol 単位の失敗処理

各行（symbol）は独立。バッチ全体は **部分成功可**。

| 結果 | 動作 |
|---|---|
| transport / parse / validation 失敗 | 当該 symbol のみ `failed` · **他 symbol は継続しない**（1 run = 1 write 前提） |
| gate 不足 | `validation_error` · **HTTP/write ゼロ** |
| write 成功 | `outputs/market_data/us_daily_bars/{SYMBOL}.json`（**gitignore** · コミット禁止） |
| write 拒否 | 理由コードを行に記録 · ディスク不変 |

失敗行列: [docs/12](./12_us_provider_failure_operator_playbook.md) · batch の `operator_summary` バケットを流用。

**監査**: run id · 開始/終了 UTC · 対象 symbol リスト · 各ゲートの満足有無 · HTTP 試行数 · write 有無 — **sanitized JSON を `outputs/ops/` 等に保存可**（secret なし · **Git 管理外**）。

---

## 9. before / after inventory smoke（必須手順）

```bash
# before（read-only）
python -m invis_alpha_os.cli.main debug us-daily-bars-cache-inventory \
  --cache-root outputs/market_data/us_daily_bars --format json \
  > /tmp/us_cache_inventory_before.json

# … 承認済み ingest（将来・単銘柄・ゲート済）…

# after（read-only）
python -m invis_alpha_os.cli.main debug us-daily-bars-cache-inventory \
  --cache-root outputs/market_data/us_daily_bars --format json \
  > /tmp/us_cache_inventory_after.json
```

**合格目安（1 銘柄 ingest 後）**:

- 当該 symbol: `missing` → `ok`（または `stale_unknown` / `insufficient` が判明したら ingest 品質を見直し）
- `summary.missing_count` が **1 減る**
- **他 symbol の status が意図せず変わらない**

---

## 10. rollback / manual quarantine

| 状況 | 手順 |
|---|---|
| **誤 write 疑い** | 当該 `{SYMBOL}.json` を **`outputs/market_data/us_daily_bars/_quarantine/`** へ手動移動（自動削除しない） |
| **検証** | inventory を再実行 · 当該 symbol が `missing` に戻ることを確認 |
| **復旧** | quarantine から戻すか、正しい payload で **単銘柄・ゲート済** 再 write |
| **git** | `outputs/` はコミットしない · `git status` で誤 add なしを確認 |

**原則**: ロールバックは **ファイル退避 + read-only inventory** で検証。バッチ「削除コマンド」は R6.16-C に含めない。

---

## 11. 実装スコープ案（別 PR · 本書では着手しない）

1. **`build_us_cache_ingest_plan(...)`** — missing-only · cap 適用 · dry-run 行列表
2. **CLI** — `debug us-cache-ingest-plan`（default dry-run）· 既存 preview/smoke への薄いラッパ
3. **tests** — cap · gate 拒否 · no HTTP（default）· inventory 連携の fixture
4. **docs** — runbook §5.2 表へのリンク

**明示しないもの**: 新 provider · スケジュール cron · daily default on。

---

## 12. runbook §7 との整合

| runbook §7 | 本設計 |
|---|---|
| operator-gated バッチ ingest | §4–§8 |
| 上限付き live HTTP | §5.1 · §7 |
| 監査ログ | §8 監査 |
| 失敗行列 docs/12 | §8 |
| R6.16-A entry criteria 済み | §1 smoke 前提 |

[docs/56](./56_r6_15_c_us_cache_population_runbook.md) §9 の「R6.16 実装」は **本書承認後**に更新する。

---

## 13. 承認チェックリスト（実装 PR 前）

- [ ] ChatGPT / オペレータ: missing 対象の **優先順位**（13 銘柄のうち最初の 1–3）
- [ ] `max_symbols_per_run` / `max_cache_writes_per_run` の確定
- [ ] `fresh enough` しきい値（日付）— inventory 拡張要否
- [ ] 本番 cache root のバックアップ方針（quarantine パス）
- [ ] R6.17（daily 接続）は **ingest 安定後・別承認**

---

## 14. 関連ドキュメント

- [docs/59](./59_r6_16_a_us_cache_inventory_mvp.md) · [docs/60](./60_r6_16_b_us_cache_inventory_hardening.md)
- [docs/11](./11_us_market_data_provider_plan.md) · [docs/12](./12_us_provider_failure_operator_playbook.md) · [docs/14](./14_us_provider_manual_live_batch_smoke_design.md) · [docs/15](./15_us_provider_manual_cache_write_evaluation_design.md)
