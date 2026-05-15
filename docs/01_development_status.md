# Development Status

## Phase 0-v1.1 — 完了（クローズ済み）

Phase 0-v1.1 は完了し、以下条件を確認済み。

- ローカルで `PYTHON=.venv/bin/python make verify` が成功すること
- GitHub Actions の `tests` workflow がグリーンであること
- `outputs/` は `.gitkeep` 等の最小限のみ Git 管理し、実行生成物は原則コミットしないこと
- `src/invis_alpha_os/data/` が Git 管理対象であり、CI で `invis_alpha_os.data` の import エラーが出ないこと
- **Observation Only + Shadow Portfolio**、**No Auto Trading** の方針を維持すること

### 完了サマリ

- 拡張可能なパッケージ骨格（`data` / `risk` / `portfolio` / `observation` 等）
- 設定テンプレート（watchlist、veto、data_confidence、market_data 等）
- CLI（`alpha-os`）と PATH 非依存の `make verify`
- Actions: `make test` + `PYTHON=python make verify`

**詳細な完了記録・障害対応一覧**: [06_phase0_completion_report.md](./06_phase0_completion_report.md)

---

## Phase 1a — 進行中

### Review Hotfix A — JST 日付ハンドリング（完了）

- **`alpha-os daily`** / **`alpha-os pack`** の**日付駆動ファイル名・見出し**は **`timezone(timedelta(hours=9))` 固定オフセット**（**`ZoneInfo` / tzdata 不使用**）で **JST 暦日**に統一。**GitHub Actions の ubuntu / UTC** でも **日本株レポートとしてのカレンダー日付**で `outputs/reports/daily/*.md` と `outputs/research_packs/*` が付く。
- **`reporting/jquants_smoke_summary.py` の `created_at`** は **UTC** のまま（保存イベント時刻；Hotfix A の対象外）。

### Review Hotfix B — safe-push selective staging（完了）

- **`scripts/safe_commit_push.sh`**：**リポジトリ全体の一括 add を廃止**し、`git status --short --untracked-files=all` 由来の **候補パスのみ** `git add --`。**index が事前に汚れている場合・競合・rename（`->`）は中断**。`DRY_RUN` も同じ列挙ロジック。

### Review Hotfix C — 安全な `.env` 読取り・短い秘密マスク（完了）

- **`scripts/load_jquants_env.py`**：`source` / eval なしで **許可 `JQUANTS_*` キーのみ**を読み、`env-doctor` / `daily-check` / `jquants-smoke` から **子プロセスへだけ**渡す。
- **`jquants_client._mask_sensitive_preview`**：短い API Key も **error 本文プレビューに出さない**。

**次の予定**: **Probe D / momentum signals** など Phase 1a 本流へ（別タスク）。

### Phase 1a Re-focus — Task 1（アルファニュメリック JP コード / 例: 285A）— 完了

- **目的**：Kioxia 型（**東証アルファニュメリック銘柄**）の **早期検知**に合わせ、**`285A`** を **`debug jquants-watchlist-bars`** の **preview / dry-run** で **`skipped_unsupported_code` にしない**。
- **`config/jp_watchlist.py`**：**`normalize_jquants_equity_code` / `jquants_daily_bars_ticker_kind`** — **ASCII `[A-Za-z0-9]{4}`** を **`ok`**（wire は **大文字**）。**記号・全角・長さ≠4・空**は **`skipped_unsupported_code`**。
- **`cli/main.py`（watchlist-bars）**：正規化後のコードで preview / **`get_daily_quotes`**。**live と実 API はテストしない**。**人手向けの任意 live は [09](./09_jquants_local_manual_test.md)** のみ。


### Task 1 — 完了（J-Quants stub・watchlist・Japan Signals）

- `docs/08_phase1a_jquants_plan.md` baseline
- `JQuantsStubAdapter`、`jp_equity`、`themes` 付き watchlist、daily「Japan Signals」

### Task 2 — 完了（real-mode skeleton + 安全ゲート）

- **`JQuantsClient`** + **`safe_auth_status()`**（**トークン実値・パスワード・raw を CLI に出さない**）
- **`debug jquants-status`**: **HTTP しない**
- **`debug jquants-daily-quotes --live`**: 実 HTTP は **`JQUANTS_ENABLED` + `JQUANTS_ALLOW_LIVE_HTTP=true` + `--live` + BASE URL +（V2）`JQUANTS_API_KEY`** の **三重ゲート**（`allow` 欠落時は `live_blocked`、URL/Key 欠落時は `not_configured`）
- **`make verify` / GitHub Actions**: 実接続なし

### Task 3 — 完了（Version2 前提の設定・手動ガイド）

- **[docs/09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)** — ローカル手動接続の手順（AI に秘密を渡さない・三重ゲート・トラブルシュート）
- **`JQUANTS_API_VERSION` / `JQUANTS_API_BASE_URL`**（`.env.example`・`JQuantsClient`）— **BASE URL 未設定時は `not_configured`**、V1 固定デフォルト URL なし
- **`config/market_data.yaml`** — `api_version`、`ci_live_http: disabled`、`manual_live_http: triple_gate_required` 等
- **実 API の本格確認は Task 5 で段階導入**

**計画・運用詳細**: [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md) · 手動確認: [09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)

### Task 4 — 完了（V2 API Key・`/equities/*` 設計寄せ）

- **`JQUANTS_API_KEY`** + HTTP ヘッダー **`x-api-key`**。**API Key 実値は標準出力・戻り値に含めない**
- **ライブ実 HTTP** は **`JQUANTS_ENABLED` + `--live` + `JQUANTS_ALLOW_LIVE_HTTP`** に加え **`BASE_URL` と `API KEY` が揃ったときのみ**（欠落時は `base_url_missing` / `api_key_missing`）
- **`_paths_for_version("v2")`** を `/equities/master`、`/equities/bars/daily` 等へ更新。V1 refresh/Bearer は **legacy（`JQUANTS_API_VERSION=v1`）**
- **本タスクでは実 API 呼び出しは行わない**（テストは mock のみ）

### Task 5 — 完了（live smoke 準備・V2 daily bars 正規化・**成功記録あり**）

- **`normalize_v2_daily_bars_response`**：`data` / `daily_quotes` / `bars` / `results` の順で **list** を検査。**空 list は `success` と `row_count=0`**。list 以外は **`invalid_response`**。
- **`get_daily_quotes`（V2 live）** の成功判定を上記に集約。**`row_count` / `source_key` / `date_from` / `date_to`** を返す（行データ・API Key は出さない）。
- **`debug jquants-daily-quotes`**：**`--live` なしは dry-run exit 0**；**一覧キーだけでなく値が配列であること**を確認してから **`success`**。CLI 出力を安全な要約のみに。**実 API は人間のローカル・手順 [09](./09_jquants_local_manual_test.md) のみ**。
- **最小 live の一例**を [09](./09_jquants_local_manual_test.md) に記録（単一コード例：**契約内日付**。Task 9.2 記録：`7011`,`6501`,`6506` / `2024-02-19` 等）。
- **テスト**：normalize・CLI `--live` exit・標準出力に秘密なし。**CI は live 不使用**。

### Task 5.6 — 完了（データ提供範囲ガード）

- **`JQUANTS_DATA_AVAILABLE_FROM` / `TO`**（任意・両方有効時のみ）で **`--date` / `--from-date` / `--to-date`** を契約ウィンドウと照合。**範囲外は `validation_error` / `date_out_of_available_range`（HTTP 前）**。**`make verify` は env 未設定の既定のまま**。
- **`config/market_data.yaml`** に env 名、**`.env.example`** に例示。

### Task 6 — 完了（watchlist・J-Quants daily bars 一括 CLI）

- **`config/jp_watchlist.py`**：`jp_watchlist` ティッカー抽出。**Phase 1a Re-focus**：**ASCII 英数字ちょうど 4 文字**を J-Quants wire へ（例：**`285A`・`7011`**、**小文字入力は正規化**）。**単体銘柄 `jquants-daily-quotes` は従来どおり桁数だけで制限しない**。
- **`alpha-os debug jquants-watchlist-bars`**：既定 **dry-run**、**`--preview-request`**（HTTP なし）、**live は三重ゲート + Task 5.6**。結果は JSON 配列。**raw・API Key なし**。

### Task 7 — 完了（daily report の J-Quants watchlist サマリ・HTTP なし）

- **`alpha-os daily`** に **J-Quants Watchlist Bars Check** セクション（**集計・`dry_run` モードの説明のみ**）。**J-Quants API には接続しない**。**`make verify` / GitHub Actions でも live しない**。
- **`reports/jquants_watchlist_daily.py`**、**`config/market_data.adapters.jquants.report`**。

### Task 8 — 完了（daily report の J-Quants readiness・HTTP なし）

- **Readiness（Green / Yellow / Red）** と **unsupported コードのみの一覧**。**live HTTP なし**（**Green でもその日に API を叩いたわけではない**）。
- **`readiness_enabled`**、**`readiness_green_requires_*`**、**`include_unsupported_codes`** 等は **`config/market_data.adapters.jquants.report`**。

### Task 9 — 完了（watchlist smoke の sanitized JSON ローカル保存）

- **`alpha-os debug jquants-watchlist-bars --save-summary`** が **`outputs/jquants_smoke/`** に **sanitized JSON** と **`latest.json`** を出力（**Git 対象外**。**API Key・raw・ヘッダー全体は書かない**）。
- **`reporting/jquants_smoke_summary.py`**。**`daily` / `make verify` / CI は変更なしで live しない**。

### Task 9.2 — 完了（契約範囲の記録・watchlist smoke 成功のドキュメント化）

- **実運用ウィンドウ（`bars` まとめ取り／HTTP 400 境界の記録を反映）**：**`.env.example`** と **[09](./09_jquants_local_manual_test.md)**・**Makefile の `jq-*` 例**の **`JQUANTS_DATA_AVAILABLE_FROM` / `FROM` 例を `2024-02-18`〜`2026-02-17`** に統一。**人間はローカル `.env` で各自のプランに合わせて上書き**。
- **watchlist limit 3** の **`--live --save-summary` 成功**（`7011` / `6501` / `6506`、`date=2024-02-19`、要約フィールドのみ）を [09](./09_jquants_local_manual_test.md) と daily レポート説明用文言に反映。**`outputs/jquants_smoke/*.json`** は **Git に載せず**。**`latest.json` も同上**。
- **`config/market_data.yaml`** に例示ウィンドウの注記。

### Task 10 — 完了（`daily` がローカル `latest.json` を参照）

- **`reports/jquants_watchlist_daily.py`**：**`latest.json` 読み取りのみ**。**`JQuantsClient.get_daily_quotes` や `urllib` は使わない**。**秘匿っぽいキー・`raw_response` キー・`raw_response_included` / `api_key_displayed` が true の場合は「unsafe summary blocked」表示**。
- **設定**：**`include_latest_smoke_summary`**、**`latest_smoke_summary_path`**、**`latest_smoke_summary_live_http: disabled`**（`config/market_data.adapters.jquants.report`）。

### Task 11 以降（未着手）

- **readiness** を **`latest.json`** の性状に合わせて **Green+ / Yellow** に細分化するか（**自動 live は禁止のまま**）。

---

## R6.6 — 285A JP momentum signals 回帰テスト（完了・main反映済み）

**コミット**: `c3eaf7b` Main R6.6: Lock 285A JP momentum regression tests
**GitHub Actions**: `tests` — success

### R6.6 で完了した内容

- **285A** が `normalize_jquants_equity_code` で `"ok"` と判定され、 `skipped_unsupported_code` にならないことを既存実装で確認
- `signals/momentum.py` に `volume_ratio_25d`・`r5/r20/r60`・`high_52w_distance_pct` が実装済みであることを確認
- `alpha-os signals` CLI が 285A を含む JP watchlist を処理することをテストで固定
- `daily` コマンドの `render_momentum_signals_cache_only_section` が 285A をキャッシュ存在時にランク出力することをテストで固定
- `volume_ratio_25d` がラストバーを prior 平均から除外していること（ルックアヘッドなし）をテストで固定

### R6.6 追加テスト（`tests/test_momentum_signals.py` / `tests/test_momentum_daily_report.py`）

- `test_285a_accepted_not_skipped_in_signals_cli`
- `test_285a_momentum_row_has_required_fields`
- `test_285a_synthetic_bars_analyze`
- `test_traditional_4digit_still_works_alongside_285a`
- `test_unsafe_symbols_rejected_signals_cli`
- `test_volume_ratio_25d_excludes_latest_bar_from_prior_average`
- `test_daily_report_momentum_section_includes_285a`

---

## R6.7 — signals CLI Phase 1a 出力確認 + `veto_status` マーカー追加（完了・main反映済み）

**コミット**: `441f004` Main R6.7 draft: Expose veto_status gap and add 285A cache-only signals test
**ブランチ**: `work/r6-7-signals-cli` → main へ fast-forward merge 済み
**GitHub Actions**: `tests` (run ID: 25861307885) — success
**テスト**: focused 44件・full suite 563件 — すべて成功

### R6.7 で完了した内容

- `alpha-os signals` CLI が Phase 1a 相当の JP momentum candidate 出力をすでに満たしていることを確認（新規実装は不要だった）
- signals JSON 出力に **`veto_status: "not_integrated_yet"`** を追加（VetoEngine未統合であることを機械可読な形で明示）
- **285A が `--source cache-only` のランク出力に出ること**をテストで固定（`test_285a_cache_only_source_appears_in_ranked`）

### R6.7 で確認した signals CLI の出力フィールド

`observation_only`、`mode`、`bars_data_source`、`veto_status`、`ranked[]` 内: `code`・`score`・`score_v2`・`labels`・`r5`・`r20`・`r60`・`high_52w_distance_pct`・`volume_ratio_25d`・`data_quality`・`bars_source`

### R6.7 でやらなかったこと（次タスクへ）

- VetoEngine の signals CLI 統合
- `signals --format markdown` の追加
- 新しい signal engine の実装
- daily report / action watchlist とのさらなる整合

---

## R6.8-A — VetoEngineをsignals CLIへ最小統合（完了・main反映済み）

**コミット**: `922badd` Main R6.8-A draft: Integrate VetoEngine into signals CLI per-ticker output
**ブランチ**: `work/r6-8-signals-veto` → main へ fast-forward merge 済み
**GitHub Actions**: `tests` (run ID: 25862111843) — success
**テスト**: full suite 565件 — すべて成功

### R6.8-Aで完了した内容

- `signals CLI`（シグナル出力コマンド）の各候補行に、銘柄別の拒否・警戒判定結果 `veto_result` を付与
- top levelの拒否判定状態 `veto_status` を `"not_integrated_yet"` → `"ok"` へ変更
- `config/veto_rules.yaml` に `hard_momentum_overheat` ルールを追加（`overheat_flag >= 1.0`）
- `MomentumBreakdown` フィールドをveto context（コンテキスト辞書）へ薄くマッピング:
  - `overheat_flag` → `1.0 / 0.0`
  - `r5` → `price_spike_5d`（絶対値）
- `overheat_flag=True` の銘柄は `hard_momentum_overheat` が発動し `veto_result.triggered=true` になる

### R6.8-Aの出力例（signals CLIの各候補行）

```json
"veto_result": {
  "triggered": true,
  "count": 1,
  "rules": [
    {
      "level": "hard_veto",
      "rule_id": "hard_momentum_overheat",
      "message": "Momentum overheat flag triggered (r20 or r60 extreme)"
    }
  ]
}
```

### R6.8-Aでやらなかったこと（次タスクへ）

- R6.8-BのMarkdown出力追加
- `veto_rules.yaml` の拡充（出来高急増ルール等）
- daily report側への `veto_result` 表示整合
- 新しいsignal engineの実装

---

## R6.8-B — signals CLIにMarkdown出力を追加（完了・main反映済み）

**コミット**: `e1005be` Main R6.8-B draft: Add --format markdown to signals CLI
**ブランチ**: `work/r6-8-b-signals-markdown` → main へ fast-forward merge 済み
**GitHub Actions**: `tests` (run ID: 25863066082) — success
**テスト**: full suite 568件 — すべて成功

### R6.8-Bで完了した内容

- `signals CLI`（シグナル出力コマンド）に `--format markdown`（Markdown形式出力指定）を追加
- `--format` 省略時は従来どおりJSON出力を維持（既存動作への影響なし）
- Markdown表の列: `# | Code | Sv2 | Labels | r5 | r20 | r60 | HiDist | VolR | Veto`
- Veto列: `veto_result.triggered=true` の場合に `⚠ rule_id` を表示
- `--source cache-only --format markdown` で実確認:
  - `285A` が表（4位）に表示される
  - `285A`・`5801` に `⚠ hard_momentum_overheat` が表示される
  - `cache_only_dry_run` モード・`observation only / Not trading advice` 表示あり

### R6.8-Bでやらなかったこと（次タスクへ）

- daily report側への `veto_result` 表示整合
- `veto_rules.yaml` の拡充・新しい拒否ルール追加
- 新しいsignal engineの実装

---

## R6.8-C — 日次レポートにVeto列を追加（完了・main反映済み）

**コミット**: `ff48e97` Main R6.8-C draft: Add Veto column to daily report Momentum Signals table
**ブランチ**: `work/r6-8-c-daily-veto-display` → main へ fast-forward merge 済み
**GitHub Actions**: `tests` (run ID: 25864075937) — success
**テスト**: full suite 570件 — すべて成功

### R6.8-Cで完了した内容

- `src/invis_alpha_os/reports/momentum_daily.py` に `_veto_cell(m: MomentumBreakdown) -> str` 関数を追加
  - `m.overheat_flag` が True → `"⚠ hard_momentum_overheat"`（モメンタム過熱による強い警戒判定）
  - False → `"—"`
- `_append_ranking_table` のヘッダーに `| Veto |` 列を追加（12列 → 13列）
- `VetoEngine`（拒否エンジン）のインポートなし。`overheat_flag` を直接参照することで依存を最小化
- `tests/test_momentum_daily_report.py` に2件のテストを追加（計15件）
  - `test_veto_cell_dash_when_no_overheat`: 通常銘柄は `—` を返すことを確認
  - `test_veto_cell_shows_overheat_rule_when_flagged`: 過熱銘柄は `⚠ hard_momentum_overheat` を返すことを確認
- 既存テスト `test_cache_only_ranking_row_has_stable_column_count` を13列対応に更新

### 日次レポート（日次レポート）での実確認

```
| 3 | 5801 | … | cache | ⚠ hard_momentum_overheat |
| 4 | 285A | … | cache | ⚠ hard_momentum_overheat |
| 5 | 5803 | … | cache | — |
```

### R6.8-Cでやらなかったこと（次タスクへ）

- `veto_rules.yaml` の拡充・新しい拒否ルール追加
- 新しいsignal engineの実装

---

## R6.8-E — `VetoEngine`（拒否・警戒判定エンジン）で `fomo_veto`（急騰追随・高値掴み警戒ルール群）を評価（完了・main反映済み）

**コミット**: `75930f8` Main R6.8-E draft: Evaluate fomo_veto section in VetoEngine
**ブランチ**: `work/r6-8-e-fomo-veto-evaluation` → main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（ブランチ push 時）**: `tests` (run ID: 25864935025) — success
**GitHub Actions（main 取り込み後 push）**: `tests` (run ID: 25865410883) — success
**テスト**: `tests/test_veto_rules.py` の focused pytest **4件** すべて成功 · full suite **573件** すべて成功

### R6.8-Eで完了した内容

- `VetoLevel`（拒否・警戒判定レベル）に `fomo_veto` を追加（`src/invis_alpha_os/core/models.py`）
- `VetoEngine.evaluate()` の評価ループに `fomo_veto` セクションを追加し、`veto_rules.yaml` の `fomo_veto` 配下ルールを `hard_veto` / `soft_veto` と同様に閾値比較する（`src/invis_alpha_os/risk/veto_rules.py`）
- `tests/test_veto_rules.py` に **3件** 追加（ファイル合計 **4件**）: `test_fomo_veto_is_evaluated` / `test_fomo_veto_does_not_fire_below_threshold` / `test_all_three_levels_can_fire_simultaneously`

### R6.8-Eでやらなかったこと（次タスクへ）

- `veto_rules.yaml` の閾値・ルール本文の変更（本タスクでは**変更なし**）
- `volume_ratio_25d` を指標とする**新規**拒否ルールの実装（モメンタム側の既存指標は対象外）
- 新しい signal engine の実装

---

## R6.8-F — 出来高急増＋短期上昇の追随警戒（`fomo_volume_price_chase`）（完了・main反映済み）

**コミット**: `7415b21` Main R6.8-F draft: FOMO volume-price chase veto via synthetic context
**ブランチ**: `work/r6-8-f-volume-spike-risk-rule` → main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（ブランチ push 時）**: `tests` (run ID: 25866028775) — success
**GitHub Actions（main 取り込み後 push）**: `tests` (run ID: 25866358212) — success
**テスト**: `tests/test_veto_rules.py` · `tests/test_momentum_daily_report.py` · `tests/test_momentum_signals.py` の focused pytest **59件** すべて成功 · full suite **577件** すべて成功

### R6.8-Fで完了した内容

- **`volume_ratio_25d`（25日平均比の出来高倍率）≥ 3.0** かつ **直近5日リターン `r5` > 0.15** のときだけ立つ合成指標 **`fomo_volume_price_chase`** を `momentum_breakdown_veto_context()`（`src/invis_alpha_os/risk/veto_rules.py`）で定義し、**`fomo_veto`（急騰追随・高値掴み警戒ルール群）** の **`fomo_volume_price_chase`（出来高急増＋短期上昇の追随警戒ルール）** として `config/veto_rules.yaml` に追加（単独の `volume_ratio_25d >= 3.0` の **`soft_veto`（弱い警戒判定）** は**実装しない**方針を維持）
- `signals`（`src/invis_alpha_os/cli/main.py`）の **`veto_result`** 経路と、日次レポート（`src/invis_alpha_os/reports/momentum_daily.py`）の **Veto列**を **`VetoEngine`（拒否・警戒判定エンジン）** 評価に揃え、`@lru_cache` で設定読み込みを日次レンダリング内で再利用
- テスト追加: `tests/test_veto_rules.py`（コンテキスト・ルール発火）· `tests/test_momentum_daily_report.py` · `tests/test_momentum_signals.py`

### R6.8-Fでやらなかったこと（次タスクへ）

- **`risk_flag`（観察用の警戒表示）** 専用の別列・別JSONチャネル（本タスクでは **`fomo_veto` の `rule_id` 表示**に統一）
- R6.9 本体の実装（並行開発の手順は **[docs/17_r6_9_parallel_development_prep.md](./17_r6_9_parallel_development_prep.md)** に整理）

---

## R6.9-A — `format_veto_table_cell`（Veto 表セル整形関数）による表示共通化（完了・main反映済み）

**コミット**: `58efc4a` Main R6.9-A draft: Share veto Markdown cell formatting  
**ブランチ**: `work/r6-9-a-veto-display-common` → main へ fast-forward merge（早送り取り込み）済み  
**GitHub Actions（R6.9-A のみ取り込み直後の `main` push）**: `tests` (run ID: 25867212766) — success  
**内容**: `signals` Markdown と日次レポートの Veto セルを **`format_veto_table_cell(veto_result)`** に集約（`VetoEngine`（拒否・警戒判定エンジン）の `veto_result` 形式に揃える）。

---

## R6.9-B — Stage 3 運用の文書化（完了・main反映済み）

**コミット（rebase 後）**: `15524c2` docs: R6.9-B Stage 3 workflow clarification (Composer2 solo) · `b1e0d4e` docs: Record R6.9-B tests workflow run id（rebase 前の `0f74f09` / `45ed3f1` と同内容）  
**ブランチ**: `work/r6-9-b-stage3-workflow-docs`（当時の **`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-9-b`）→ **R6.9-A 取り込み後の `main` 上へ rebase** のうえ main へ fast-forward merge 済み  
**内容**: **Stage 3** を「**Cursor Composer2** 単独・1 指示で検証〜 branch CI まで」と定義し、**Claude Code と Composer2 の同時並行**と誤読されないよう **[docs/17_r6_9_parallel_development_prep.md](./17_r6_9_parallel_development_prep.md)** に追記。  
**GitHub Actions（R6.9-B を含む `main` push）**: `tests` (run ID: 25867295622) — success

---

## R6.9-C — US / metals / macro / portfolio の優先順位整理（完了・main反映済み）

**コミット**: `61b3bf2` docs: R6.9-C priority landscape (US, metals, macro, portfolio)
**ブランチ**: `work/r6-9-c-priority-docs` → main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（branch push 時）**: `tests` (run ID: 25867473310) — success
**GitHub Actions（`main` 取り込み直後の push）**: `tests` (run ID: 25889946086) — success
**内容**: **[docs/18_r6_9_c_priority_us_metals_macro_portfolio.md](./18_r6_9_c_priority_us_metals_macro_portfolio.md)** に **US → portfolio → macro → metals** の優先度メモを整理。**実装・live HTTP（実ネットワーク接続）・production cache write（本番キャッシュ書き込み）は追加していない**。

### 次タスク（候補）

- **US equities** の **cache-only** 読み取り以外（**CLI 配線**・**日次レポート**等）は **R6.10-B 以降**で個別判断。

---

## R6.10-A — US equities cache-only MVP（完了・main反映済み）

**コミット**: `3438268` Main R6.10-A draft: Add US equities cache-only MVP scaffold · `90e78d7` docs: Record R6.10-A branch CI run id · `6a86f82` docs: Record R6.10-A main merge completion
**ブランチ**: `work/r6-10-a-us-equities-cache-only-mvp`（当時の **`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-10-a`）→ main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（branch push 時）**: `tests` (run ID: 25890095708) — success
**GitHub Actions（`main` 取り込み直後の push）**: `tests` (run ID: 25890235423) — success
**GitHub Actions（完了 docs push）**: `tests` (run ID: 25890275877) — success
**内容**: **`parse_us_daily_bars_payload`** / **`load_us_daily_bars_json_file`**（`src/invis_alpha_os/data/us_daily_bars_cache.py`）と **`tests/test_us_equities_cache.py`**、設計メモ **[docs/19_r6_10_a_us_equities_cache_only_mvp.md](./19_r6_10_a_us_equities_cache_only_mvp.md)**。**live HTTP（実ネットワーク接続）・production cache write（本番キャッシュ書き込み）・CLI 統合なし**。

---

## R6.10-B — US equities cache-only validation hardening（完了・main反映済み）

**コミット**: `e37c38f` Main R6.10-B draft: Harden US equities cache-only validation
**ブランチ**: `work/r6-10-b-us-equities-cache-hardening`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-10-b`）→ main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（branch push 時）**: `tests` (run ID: 25917456523) — success
**GitHub Actions（`main` 取り込み直後の push）**: `tests` (run ID: 25917862396) — success
**focused test**: `tests/test_us_equities_cache.py` · `tests/test_us_daily_bars_cache.py` — 16 passed
**内容**: **`_us_daily_bar_rows_valid`** · **`bar_count` 整合** · 重複日付拒否 · 日付昇順チェック · **`tests/fixtures/us_equities/minimal_msft_envelope.json`** · edge case regression。詳細は **[docs/20_r6_10_b_us_equities_cache_hardening.md](./20_r6_10_b_us_equities_cache_hardening.md)**。**live HTTP・production cache write・CLI / report 統合・JP momentum / Veto 変更なし**。

### 次タスク（候補）

- **R6.10-C**: US equities cache-only layer の **preview / diagnostics** 入口（fixture / cache JSON の短い要約）。CLI に自然に入らない場合は pure helper + docs のみ。

---

## R6.10-C — US equities cache-only preview / diagnostics（完了・main反映済み）

**コミット**: `ec5a2af` Main R6.10-C draft: Add US cache-only CLI preview
**ブランチ**: `work/r6-10-c-us-equities-cache-preview`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-10-c`）→ main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（branch push 時）**: `tests` (run ID: 25917974312) — success
**focused test**: `tests/test_us_equities_cache.py` · `tests/test_us_daily_bars_cache.py` · `tests/test_cli_us_daily_bars_cache_preview.py` — 25 passed · full pytest 599 passed
**内容**: **`debug us-daily-bars-cache-preview`** · **`build_us_daily_bars_cache_preview`** 等（**markdown / json** 出力）。詳細は **[docs/21_r6_10_c_us_equities_cache_preview.md](./21_r6_10_c_us_equities_cache_preview.md)**。**live HTTP・production cache write・US scoring・JP momentum / Veto 変更なし**。

### 次タスク（候補）

- **R6.10-D**: US cache preview / diagnostics の **hardening**（出力契約・異常系・CLI 回帰テスト）。

---

## R6.10-D — US cache preview hardening（完了・main反映済み）

**コミット**: `c2f2a8b` Main R6.10-D draft: Harden US cache preview CLI tests
**ブランチ**: `work/r6-10-d-us-cache-preview-hardening` → main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（branch push 時）**: `tests` (run ID: 25918269794) — success
**focused test**: preview + US cache tests — **35 passed** · full pytest **609 passed**
**内容**: **`PREVIEW_OK_KEYS`** / **`PREVIEW_INVALID_BASE_KEYS`** · CLI 異常系・JSON/Markdown 契約テスト。詳細は **[docs/22_r6_10_d_us_cache_preview_hardening.md](./22_r6_10_d_us_cache_preview_hardening.md)**。**live HTTP・production cache write・JP momentum / Veto 変更なし**。

### 次タスク（候補）

- **R6.10-E**: US daily bars **cache-only basic metrics** MVP（pure function + fixture test）。

---

## R6.10-E — US cache-only basic metrics MVP（完了・main反映済み）

**コミット**: `a7fd315` Main R6.10-E draft: Add US cache-only basic metrics
**ブランチ**: `work/r6-10-e-us-cache-basic-metrics` → main へ fast-forward merge（早送り取り込み）済み
**GitHub Actions（branch push 時）**: `tests` (run ID: 25918535243) — success
**focused test**: US cache + preview + metrics — **40 passed** · full pytest **614 passed**
**内容**: **`compute_us_daily_bars_basic_metrics`**（`us_daily_bars_metrics.py`）。`total_return` / `return_5d` / `return_20d` / `has_5d` / `has_20d`。詳細は **[docs/23_r6_10_e_us_cache_basic_metrics.md](./23_r6_10_e_us_cache_basic_metrics.md)**。**live HTTP・production cache write・JP momentum / Veto 変更なし**。

### 次タスク（候補）

- **R6.10-F**: basic metrics を preview / diagnostics へ安全接続（既存 preview デフォルト出力は非破壊）。

---

<<<<<<< HEAD
## R6.10-F — US cache metrics preview integration（完了・main反映済み）

**コミット**: `13e1b6b` Main R6.10-F draft: Add US cache metrics debug command（rebase 後・元 branch CI `8db961a` / run `25918932189`）
**ブランチ**: `work/r6-10-f-us-cache-metrics-preview` → main へ取り込み（`29140cd` 上に rebase 後 fast-forward）
**内容**: **`debug us-daily-bars-cache-metrics`** · **`METRICS_PREVIEW_OK_KEYS`** · preview デフォルト非変更。詳細は **[docs/24_r6_10_f_us_cache_metrics_preview.md](./24_r6_10_f_us_cache_metrics_preview.md)**。

### 次タスク（候補）

- **R6.10-G**: metrics command の出力契約・異常系・回帰テスト強化。
=======
## R6.10-F — US cache metrics preview integration（main 反映済み・`13e1b6b`）

詳細は **[docs/24_r6_10_f_us_cache_metrics_preview.md](./24_r6_10_f_us_cache_metrics_preview.md)**。

---

## R6.10-G — US cache metrics command hardening（作業ブランチ・`main` 未反映）

**ブランチ**: `work/r6-10-g-us-cache-metrics-command-hardening`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-10-g`）
**方針**: パターンA。詳細は **[docs/25_r6_10_g_us_cache_metrics_command_hardening.md](./25_r6_10_g_us_cache_metrics_command_hardening.md)**。
>>>>>>> 8c9cc99 (Main R6.10-G draft: Harden US cache metrics command)

---

## R6.8以降の候補タスク（未着手）

優先度は状況に応じて判断してください。

**候補（veto 拡張の残り）**: `veto_rules.yaml` の閾値調整・追加ルール（例: より保守的な単独閾値、`overheat_flag` との組み合わせ）。**R6.8-F** で複合条件の出来高＋短期上昇は実装済みのため、次は過検知・表示優先度の設計レビューから入るとよい。

**その後**: signals CLI / daily report / action watchlistの表示整合（R6.8-C以降で順次対応）。

**並行開発の進め方**: [docs/17_r6_9_parallel_development_prep.md](./17_r6_9_parallel_development_prep.md)（**R6.9 実装は ChatGPT 確認後に開始**。本ドキュメントは準備メモのみ）

---

## AI向け作業指示言語の運用方針（R6.7以降）

- Claude Code / Cursor / Codex への指示は、原則として**日本語**で書く
- ただし、以下は原文のまま維持する:
  - Gitコマンド・ブランチ名・コミットID・ファイルパス
  - ワークフロー名・テストコマンド・CLI名
  - コード内文字列・JSONキー
  - エラーメッセージ

---

## DevOps — ローカル運用ショートカット（完了）

- **Makefile**：**`make env-doctor`**、**`make daily-check`**、**`make jquants-smoke-dry-run`**（必須 `DATE`,`LIMIT`。**dry-run + `--save-summary`**のみ）、**`make jquants-smoke-live`**（**`CONFIRM_LIVE_HTTP=YES`** 必須。子プロセスのみ **`JQUANTS_ALLOW_LIVE_HTTP=true`** + **`--live --save-summary`**）、**`make post-push-check`**（`gh` 任意）、**`make ops-check`**（上記 3 を **live HTTP なし**で順実行）。
- **スクリプト**：`scripts/env_doctor.sh` / `daily_check.sh` / `jquants_smoke.sh` / `post_push_check.sh`。**`.env` 全文や API Key 実値は出さない**。禁止の **`rm`/`rm -rf`** は不使用。
- **外部レビュー用まとめ**：[docs/10_system_overview_for_external_review.md](./10_system_overview_for_external_review.md)

関連: [07_ai_development_workflow.md](./07_ai_development_workflow.md)
