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

## R6.9-A — Veto 表示ロジック共通化（完了・main反映済み）

**コミット（Markdown セル）**: `58efc4a` · **rescue（`veto_result` dict）**: `10d9701`（rebase 後 · stale `5c45103` は直接 merge せず rescue 経由）  
**ブランチ**: `work/r6-9-a-veto-result-centralization-rebase` · branch CI `25923815461` · main CI `25924233571`  
**内容**: `format_veto_table_cell` · `veto_hits_to_result_dict` · `build_momentum_veto_result` — signals JSON / Markdown / daily report の `veto_result` 形状を統一。  
**stale 整理**: `work/r6-9-a-veto-display-common` / `5c45103` は **merge 禁止**（参照のみ · worktree 削除候補）。

---

## R6.12-QA — FOMO Veto 意味論ホットフィックス（完了・main反映済み）

**コミット**: `b8f78ae` Main R6.12-QA draft: Fix FOMO veto semantics and centralize veto result（branch CI `25924540654` · main CI 反映後 docs 追記）  
**ブランチ**: `work/r6-12-veto-fomo-centralization-hotfix`  
**内容**: `config/veto_rules.yaml` から **`fomo_chase_warning`** を削除し **`fomo_volume_price_chase`** に一本化（急落誤発火解消）。`risk/__init__.py` export 追加。R6.9-A rescue（`10d9701`）は作業開始時点で main 済み。stale `work/r6-9-a-veto-display-common` / `5c45103` は **merge 禁止**。  
**検証**: focused 65 passed · full pytest **684** passed · agent-final-check success · live HTTP なし · production cache write なし。

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

## R6.10-F — US cache metrics preview integration（完了・main反映済み）

**コミット**: `13e1b6b` Main R6.10-F draft: Add US cache metrics debug command
**内容**: **`debug us-daily-bars-cache-metrics`** · **`METRICS_PREVIEW_OK_KEYS`**。詳細は **[docs/24_r6_10_f_us_cache_metrics_preview.md](./24_r6_10_f_us_cache_metrics_preview.md)**。

---

## R6.10-G — US cache metrics command hardening（完了・main反映済み）

**コミット**: `47d95b8` Main R6.10-G draft: Harden US cache metrics command（branch CI `25919232539`）
**内容**: **`METRICS_PREVIEW_INVALID_BASE_KEYS`** · CLI 異常系テスト拡充。詳細は **[docs/25_r6_10_g_us_cache_metrics_command_hardening.md](./25_r6_10_g_us_cache_metrics_command_hardening.md)**。

### 次タスク（候補）

- **R6.11-C**: US signals regression plan（完了後は R6.11-D）。

---

## R6.10-H — US cache metrics examples（完了・main反映済み）

**コミット**: `fa6f1d3` Main R6.10-H draft: Add US cache metrics examples and regression fixtures（branch CI `25919651109`）
**内容**: **`msft_25bars_metrics_envelope.json`** · JSON/Markdown golden-style 回帰 · 詳細は **[docs/26_r6_10_h_us_cache_metrics_examples.md](./26_r6_10_h_us_cache_metrics_examples.md)**。

### 次タスク（候補）

- **R6.11-B**: US cache-only signals pure helper MVP（本ブランチ設計 docs 参照）。

---

## R6.11-A — US signals boundary / roadmap（完了・main反映済み）

**コミット**: `92d0a10` docs: R6.11-A US signals boundary roadmap（branch CI `25920084716`）
**内容**: Data→Metrics→Signals 層分離 · R6.11-B以降ロードマップ。詳細は **[docs/27_r6_11_a_us_signals_boundary_roadmap.md](./27_r6_11_a_us_signals_boundary_roadmap.md)**。

### 次タスク（候補）

- **R6.11-D**: US signals golden regression + debug CLI MVP。

---

## R6.11-B — US cache-only signals pure helper MVP（完了・main反映済み）

**コミット**: `c0dbbb3` Main R6.11-B draft: Add US cache-only signals pure helper MVP（branch CI `25920373609`）
**内容**: `compute_us_cache_signal_row` · `US_CACHE_SIGNAL_ROW_OK_KEYS` · `momentum_label`（観測用）。詳細は **[docs/28_r6_11_b_us_cache_signals_pure_helper.md](./28_r6_11_b_us_cache_signals_pure_helper.md)**。

### 次タスク（候補）

- **R6.11-C**: regression / golden / CLI 計画 docs。

---

## R6.11-C — US signals regression plan（完了・main反映済み）

**コミット**: `1c5eb4e` docs: R6.11-C US signals regression plan（rebase 後 · branch CI `25920419029`）
**内容**: golden / CLI 次タスク計画。詳細は **[docs/29_r6_11_c_us_signals_regression_plan.md](./29_r6_11_c_us_signals_regression_plan.md)**。

### 次タスク（候補）

- **R6.11-F**: US asset universe fixture / metadata（作業ブランチ候補）。

---

## R6.11-D — US cache signals debug CLI（完了・main反映済み）

**コミット**: `1c9ce04` Main R6.11-D draft: Add US cache signals debug CLI（branch CI `25920687460`）
**内容**: `debug us-cache-signals-preview` · golden 回帰 · 詳細は **[docs/30_r6_11_d_us_signals_debug_cli.md](./30_r6_11_d_us_signals_debug_cli.md)**。

### 次タスク（候補）

- **R6.11-F**: US asset universe fixture / metadata。

---

## R6.11-E — US equity / ETF policy and report staging（完了・main反映済み）

**コミット**: `bf9968d` docs: R6.11-E US ETF and report boundary（branch CI `25920960706`）
**内容**: equity/ETF 同一 cache · `asset_class` 方針 · report 段階接続。詳細は **[docs/31_r6_11_e_us_etf_report_boundary.md](./31_r6_11_e_us_etf_report_boundary.md)**。

### 次タスク（候補）

- **R6.11-G**: report section dry-run 設計（本ブランチ設計 docs 参照）。

---

## R6.11-F — US asset universe fixture / metadata（完了・main反映済み）

**コミット**: `adb1879` Main R6.11-F draft: Add US asset universe loader（branch CI `25921366337` · main CI `25921579826` · 完了 docs `5f507a9`）
**内容**: `us_asset_universe.py` · `us_asset_universe_minimal.json`（16 entries）· parse / load / index / enabled symbols。live HTTP なし · production cache write なし · report / Veto / portfolio / macro 未接続。詳細は **[docs/32_r6_11_f_us_asset_universe_fixture.md](./32_r6_11_f_us_asset_universe_fixture.md)**。
**検証**: focused 22 passed · full pytest 655 passed · agent-final-check success。

### 次タスク（候補）

- **R6.12-D**: daily report opt-in design（作業ブランチ候補）。

---

## R6.11-G — Universe-aware US signals preview（完了・main反映済み）

**コミット**: `d6221ca`（rebase 後 · original `e04cbc7`）Main R6.11-G draft: Add universe-aware US signals preview（branch CI `25921702389` · main CI `25921938640`）
**内容**: `--universe-path` · `attach_us_asset_universe_metadata_to_signals_preview` · `US_CACHE_SIGNALS_UNIVERSE_EXTRA_KEYS` · default 非破壊 · `universe_status` matched/disabled/not_found · invalid universe → `universe_invalid`。live HTTP なし · production cache write なし · report / Veto / portfolio / macro 未接続。詳細は **[docs/33_r6_11_g_universe_aware_us_signals_preview.md](./33_r6_11_g_universe_aware_us_signals_preview.md)**。
**検証**: focused 29 passed · full pytest 662 passed · agent-final-check success。

### 次タスク（候補）

- **R6.12-A**: US signals report dry-run MVP（作業ブランチ候補）。

---

## R6.11-H — Universe edge-case golden hardening（完了・main反映済み）

**コミット**: `5f546bd` Main R6.11-H draft: Harden universe-aware signal preview edge cases（branch CI `25922035968` · main CI `25922292372`）
**内容**: `us_asset_universe_msft_disabled.json` · disabled / skipped+universe / invalid universe golden · `asset_class` 優先順位 docs。live HTTP なし · production cache write なし · report / Veto / portfolio / macro 未接続。詳細は **[docs/34_r6_11_h_universe_edge_golden_hardening.md](./34_r6_11_h_universe_edge_golden_hardening.md)**。
**検証**: focused 36 passed · full pytest 669 passed · agent-final-check success。

### 次タスク（候補）

- **R6.12-C**: US signals batch manifest helper（作業ブランチ候補）。

---

## R6.12-A — US signals report dry-run MVP（完了・main反映済み）

**コミット**: `6545bbf` Main R6.12-A draft: Add US signals report dry-run renderer（branch CI `25922379413` · main CI `25922649486`）
**内容**: `render_us_cache_signals_dry_run_section` · 単一 symbol 表形式 · daily report 未接続。詳細は **[docs/35_r6_12_a_us_signals_report_dry_run.md](./35_r6_12_a_us_signals_report_dry_run.md)**。
**検証**: focused 34 passed · full pytest 673 passed · agent-final-check success。

### 次タスク（候補）

- **R6.12-C**: US signals batch manifest helper。

---

## R6.12-B — Multi-symbol US signals report dry-run（完了・main反映済み）

**コミット**: `11c676c` Main R6.12-B draft: Add multi-symbol US signals dry-run renderer（branch CI `25922726298` · main CI `25922972372`）
**内容**: `render_us_cache_signals_multi_symbol_dry_run_section` · 単一 symbol API 非破壊 · 空リスト対応。live HTTP なし · daily report 未接続。詳細は **[docs/36_r6_12_b_us_signals_multisymbol_dry_run.md](./36_r6_12_b_us_signals_multisymbol_dry_run.md)**。
**検証**: dry-run tests 6 passed · full pytest 675 passed · agent-final-check success。

### 次タスク（候補）

- **R6.12-E**: opt-in implementation（候補）。

---

## R6.12-C — US signals batch manifest helper（完了・main反映済み）

**コミット**: `d88c9e0` Main R6.12-C draft: Add US signals batch manifest helper（branch CI `25923059540` · main CI `25924122523`）
**内容**: `build_us_cache_signals_previews_from_batch_manifest` · `entries[]` `{ symbol, cache_path }` · optional `universe_path` · `path_base` repo root · 自動走査なし。live HTTP なし · daily report / CLI 未接続。詳細は **[docs/37_r6_12_c_us_signals_batch_manifest.md](./37_r6_12_c_us_signals_batch_manifest.md)**。
**検証**: focused 11 passed · full pytest 680 passed · agent-final-check success。

### 次タスク（候補）

- **R6.12-E**: opt-in implementation。

---

## R6.12-D — US daily report opt-in design（完了・main反映済み）

**コミット**: `1e4013c` docs: R6.12-D US report opt-in design（branch CI `25924652445` · main CI 反映後 docs 追記）  
**内容**: daily report opt-in 設計（実装なし）。manifest → batch builder → multi-symbol renderer · CLI `--us-signals-dry-run-manifest` 推奨 · default 非変更。詳細は **[docs/38_r6_12_d_us_report_opt_in_design.md](./38_r6_12_d_us_report_opt_in_design.md)**。  
**検証**: full pytest 684 passed · docs-only · live HTTP なし · production cache write なし。

### 次タスク（候補）

- **R6.13-A**: momentum + JQ + US opt-in **結合順** goldenは **完了**（`main`）。

---

## R6.12-E — US daily report opt-in CLI（完了・main反映済み）

**コミット**: `4b0aee8` Main R6.12-E draft: Add US signals dry-run report opt-in helper（branch CI `25924983580` · main CI `25943855800` · 完了 docs `8232f4c` / CI `25943892971`）
**ブランチ**: `work/r6-12-e-us-report-opt-in-cli`（当初 **`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-12-e`** · **R6.14-H で worktree remove 済み**）
**内容**: `daily --us-signals-dry-run-manifest` · `append_us_signals_dry_run_section` · flag なし default **byte 同一**（二重 invoke テスト）· invalid manifest は skip · **exit 0**。live HTTP なし · production cache write なし · Veto / portfolio / macro 未接続。詳細は **[docs/39_r6_12_e_us_report_opt_in_cli.md](./39_r6_12_e_us_report_opt_in_cli.md)**。
**検証**: focused 33 passed · full pytest **690** passed · agent-final-check success。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch proposal（**別承認**）。

---

## R6.12-F — US report opt-in hardening design（完了・main反映済み）

**コミット**: `2b2c1f7` docs: R6.12-F US report opt-in hardening design（branch CI `25925044617` · main merge CI `25943934851` · 完了 docs `32c320f`）
**ブランチ**: `work/r6-12-f-us-report-opt-in-hardening-design`（当初 **`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-12-f`** · **R6.14-F で worktree remove 済み**）
**内容**: R6.12-E 後の hardening 計画（docs-only）。詳細は **[docs/40_r6_12_f_us_report_opt_in_hardening_design.md](./40_r6_12_f_us_report_opt_in_hardening_design.md)**。
**検証**: full pytest **690** passed · docs-only · live HTTP なし · production cache write なし。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch proposal（**別承認**）。

---

## R6.12-G — US report opt-in golden coverage（完了・main反映済み）

**コミット**: `52d3d49` Main R6.12-G draft: Harden US report opt-in golden coverage（branch CI `25944029730` · main CI `25944228048`）
**ブランチ**: `work/r6-12-g-us-report-opt-in-hardening`（当初 **`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-12-g`** · **R6.14-G で worktree remove 済み**）
**内容**: `_GOLDEN_DAILY_BODY_NO_OPTS` · invalid appendix snapshot · `_daily_body` 読み戻しを **`cli_main.today_jst_iso()`** と整合。**product code 変更なし**。詳細は **[docs/41_r6_12_g_us_report_opt_in_hardening.md](./41_r6_12_g_us_report_opt_in_hardening.md)**。
**検証**: focused 35 · full pytest **692** · agent-final-check success · live HTTP / production cache write なし。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch proposal（**別承認**）。

---

## R6.13-A — Daily integrated US opt-in golden（完了・main反映済み）

**コミット**: `6ab8db1` Main R6.13-A draft: Add daily US opt-in integrated golden coverage（branch CI `25944357356` · main merge push CI **`25944670951`**）
**ブランチ**: `work/r6-13-a-daily-us-opt-in-integrated-golden`（当初 **`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-13-a`** · **R6.14-E で worktree remove 済み**）
**内容**: JQ watchlist 節 · momentum 両節 · `--us-signals-dry-run-manifest` 指定時の **`##` / `###`** 見出し順固定（日付 `2031-07-15`）。live HTTP／production cache write／Veto・portfolio・macro **なし**。詳細は **[docs/42_r6_13_a_daily_us_opt_in_integrated_golden.md](./42_r6_13_a_daily_us_opt_in_integrated_golden.md)**。
**検証**: focused **37 passed** · full pytest **694 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch proposal（**別承認**）。

---

## R6.13-B — US report opt-in operational readiness（完了・main反映済み）

**コミット（main 取り込み）**: `f42ccf6` Main R6.13-B draft: Add US report opt-in operational readiness coverage（**clean squash branch** `work/r6-13-b-us-report-opt-in-operational-readiness-squash` · branch CI **`25945006838`** · main merge push CI **`25945039205`**）
**original branch（直接 main merge なし）**: `work/r6-13-b-us-report-opt-in-operational-readiness`（最終 `fa2741f` · branch CI **`25944862016`** success）
**squash worktree**: `/Users/uotani/Projects/invest-alpha-os-r6-13-b-squash`
**内容**: **`daily --us-signals-dry-run-manifest`** の runbook 固定 · invalid／スキーマ不一致時 **exit 0** + `manifest_invalid` · Typer／Click **Option 登録**でヘルプ文字列依存を回避（smoke）。**default daily 非変更**。**product code 変更なし**。詳細は **[docs/43_r6_13_b_us_report_opt_in_operational_readiness.md](./43_r6_13_b_us_report_opt_in_operational_readiness.md)**。
**検証**: focused **29 passed** · full pytest **697 passed** · agent-final-check success · live HTTP／production cache write／Veto・portfolio・macro **なし**。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch proposal（**別承認**）。

---

## R6.13-C — Project cleanup readiness（完了・main反映済み）

**コミット**: `d034d16` docs: R6.13-C project cleanup readiness（branch CI **`25945163275`** · main merge push CI **`25945280440`**）
**ブランチ**: `work/r6-13-c-project-cleanup-readiness`（当初 **`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-13-c`** · **R6.14-D で worktree remove 済み**）
**内容**: 旧 worktree／stale branch／untracked review docs の **整理方針を docs-only で明文化**。**本タスクでは削除操作なし**。stale **`5c45103` merge 禁止** · `r6-10-g` 競合マーカーは **`main` とは別問題**。詳細は **[docs/44_r6_13_c_project_cleanup_readiness.md](./44_r6_13_c_project_cleanup_readiness.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch cleanup proposal（**別承認**）。

---

## R6.14-A — Cleanup preflight inventory（完了・main反映済み）

**コミット**: `cc33ef1` docs: R6.14-A cleanup preflight inventory（branch CI **`25945410481`** · main merge push CI **`25945536823`**）
**ブランチ**: `work/r6-14-a-cleanup-preflight-inventory`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-a`）
**内容**: worktree／branch／`review_integrated_*.md` の **棚卸し表と分類案**。**削除操作なし**。**`review_integrated` はコミット禁止**。詳細は **[docs/45_r6_14_a_cleanup_preflight_inventory.md](./45_r6_14_a_cleanup_preflight_inventory.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch cleanup proposal（**別承認**）。

---

## R6.14-B — Cleanup execution proposal（完了・main反映済み）

**コミット**: `55d1a75` docs: R6.14-B cleanup execution proposal（branch CI **`25945653660`** · main merge push CI **`25945800846`**）
**ブランチ**: `work/r6-14-b-cleanup-execution-proposal`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-b`）
**内容**: R6.14-A inventory を踏まえた **削除実行前のコマンド案・承認ゲート**（**本タスクではコマンド実行なし**）。詳細は **[docs/46_r6_14_b_cleanup_execution_proposal.md](./46_r6_14_b_cleanup_execution_proposal.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch cleanup proposal（**別承認**）。

---

## R6.14-C — Approved single worktree cleanup（完了・main反映済み）

**コミット（`main` 取り込み）**: `b5a6e0f` docs: R6.14-C approved single worktree cleanup（branch CI **`25945920148`** · main merge push CI **`25946097150`**）· **完了記録**: `docs: Record R6.14-C main completion`
**ブランチ**: `work/r6-14-c-approved-single-worktree-cleanup`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-c`）
**内容**: 承認済み **`/Users/uotani/Projects/invest-alpha-os-r6-13-b-squash` のみ** `git worktree remove`（**1 回**）。**branch / remote branch 削除なし** · **`rm -rf` なし**。詳細は **[docs/47_r6_14_c_approved_single_worktree_cleanup.md](./47_r6_14_c_approved_single_worktree_cleanup.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch cleanup proposal（**別承認**）。

---

## R6.14-D — Approved single worktree cleanup（完了・main反映済み）

**コミット（`main` 取り込み）**: `1dcc253` docs: R6.14-D approved single worktree cleanup（branch CI **`25946270795`** · main merge push CI **`25950244257`**）· **完了記録**: `docs: Record R6.14-D main completion`
**ブランチ**: `work/r6-14-d-approved-single-worktree-cleanup`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-d`）
**内容**: 承認済み **`/Users/uotani/Projects/invest-alpha-os-r6-13-c` のみ** `git worktree remove`（**1 回**）。**branch / remote branch 削除なし** · **`rm -rf` なし**。詳細は **[docs/48_r6_14_d_approved_single_worktree_cleanup.md](./48_r6_14_d_approved_single_worktree_cleanup.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-M**: next single cleanup or branch cleanup proposal（**別承認**）。

---

## R6.14-E — Approved single worktree cleanup（完了・main反映済み）

**コミット（`main` 取り込み）**: `11d12e8` docs: R6.14-E approved single worktree cleanup（branch CI **`25950345142`** · main merge push CI **`25950505290`**）· **完了記録**: `docs: Record R6.14-E main completion`
**ブランチ**: `work/r6-14-e-approved-single-worktree-cleanup`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-e`）
**内容**: 承認済み **`/Users/uotani/Projects/invest-alpha-os-r6-13-a` のみ** `git worktree remove`（**1 回**）。**branch / remote branch 削除なし** · **`rm -rf` なし**。詳細は **[docs/49_r6_14_e_approved_single_worktree_cleanup.md](./49_r6_14_e_approved_single_worktree_cleanup.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-K**: next single cleanup or follow-up proposal（**別承認**）。

---

## R6.14-F — Approved single old R6.12 worktree cleanup（完了・main反映済み）

**コミット（`main` に取り込み）**: `63975b5` **`docs` 整形のみの追記**（親 `61e9715` と合わせ `docs` 追加）・ branch CI **`25950588454`** / **`25950660767`** · main merge push CI **`25950681929`** · **完了記録**: `docs: Record R6.14-F main completion`
**ブランチ**: `work/r6-14-f-approved-single-worktree-cleanup`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-f`）
**内容**: **`/Users/uotani/Projects/invest-alpha-os-r6-12-f` のみ** `git worktree remove`（**1 回**。**docs-only の R6.12-F（design）** worktree を選定）。詳細は **[docs/50_r6_14_f_approved_single_worktree_cleanup.md](./50_r6_14_f_approved_single_worktree_cleanup.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-K**: next single cleanup or follow-up proposal（**別承認**）。

---

## R6.14-G — Approved single old R6.12 worktree cleanup（完了・main反映済み）

**コミット（`main` 取り込み）**: `488abfe` docs: R6.14-G approved single worktree cleanup（branch CI **`25950768633`** · main merge push CI **`25950906910`**）· **完了記録**: `docs: Record R6.14-G main completion`
**ブランチ**: `work/r6-14-g-approved-single-worktree-cleanup`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-g`）
**内容**: **`/Users/uotani/Projects/invest-alpha-os-r6-12-g` のみ** `git worktree remove`（**1 回**）。詳細は **[docs/51_r6_14_g_approved_single_worktree_cleanup.md](./51_r6_14_g_approved_single_worktree_cleanup.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-J**: **next single cleanup** または **ユーザー承認付き `r6-10-g` の単一 worktree remove**（**別承認**）。詳細は **[docs/53_r6_14_i_approved_single_worktree_cleanup.md](./53_r6_14_i_approved_single_worktree_cleanup.md)**。
- **R6.15-A**: **`work/r6-15-a-daily-header-and-stale-output-fix`** — daily 冒頭文言と stale output（ブランチ作業のみ・**別承認**）。

---

## R6.14-H — Approved single R6.12 cleanup and **`r6-10-g`** decision（完了・main反映済み）

**コミット（`main` 取り込み）**: `bf75781` docs: R6.14-H approved single cleanup and `r6-10-g` decision（branch CI **`25951001581`** · main merge push CI **`25951076732`**）· **完了記録**: **`docs: Record R6.14-H main completion`**
**ブランチ**: `work/r6-14-h-approved-single-worktree-cleanup-and-r6-10-g-decision`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-h`）
**内容**: **`/Users/uotani/Projects/invest-alpha-os-r6-12-e` のみ** `git worktree remove`。**`r6-10-g`** は docs decision のみ（**未削除・未修復**）。詳細は **[docs/52_r6_14_h_approved_single_worktree_cleanup_and_r6_10_g_decision.md](./52_r6_14_h_approved_single_worktree_cleanup_and_r6_10_g_decision.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-J**: **next single cleanup**（R12 残余）。
- **R6.15-A**: **`work/r6-15-a-daily-header-and-stale-output-fix`** — daily 冒頭文言と stale output（ブランチ作業のみ）。

---

## R6.14-I — Approved single old R6.12 worktree cleanup（完了・main反映済み）

**コミット（`main` 取り込み）**: `304b822` docs: R6.14-I approved single worktree cleanup（branch CI **`25951158250`** · main merge push CI **`25951287619`**）· **完了記録**: **`docs: Record R6.14-I main completion`**
**ブランチ**: `work/r6-14-i-approved-single-worktree-cleanup`（**`git worktree`**: `/Users/uotani/Projects/invest-alpha-os-r6-14-i`）
**内容**: **`/Users/uotani/Projects/invest-alpha-os-r6-12-d` のみ** `git worktree remove`（**1 回**）。**`git worktree remove --force`** および **`rm -rf` なし**。**branch / remote branch 明示削除なし**。詳細は **[docs/53_r6_14_i_approved_single_worktree_cleanup.md](./53_r6_14_i_approved_single_worktree_cleanup.md)**。
**検証**: full pytest **697 passed** · agent-final-check success。

### 次タスク（候補）

- **R6.14-J**：R12 の **next single cleanup**。**R6.15-A** と独立。

---

## R6.15-A — Daily header · stale outputs · review record（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`587bd82`** · PR **#1** squash merge · main push CI **`26032578030`** success。
**内容**: daily 冒頭文案更新 · stale **`2031-07-15`** outputs 整理 · **`docs/review_integrated_20260515.md`** を Git 管理。詳細は **[docs/54_r6_15_a_daily_header_stale_output_review_record.md](./54_r6_15_a_daily_header_stale_output_review_record.md)**。

### 次タスク（候補）

- **R6.15-D**: Codex light review prompt（ブランチ作業中）。

---

## R6.15-B — Safety gate automation（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`e6e10c5`** · PR **#2** squash merge · main push CI **`26032950089`** success。
**内容**: **`make main-gate`** · **`scripts/main_gate.sh`** · **`.pre-commit-config.yaml`**。詳細は **[docs/55_r6_15_b_safety_gate_automation.md](./55_r6_15_b_safety_gate_automation.md)**。

### 次タスク（候補）

- **R6.15-D** Codex review pack。

---

## R6.15-C — US cache population runbook（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`f6250d8`** · PR **#3** squash merge · branch CI **`26034938282`** · main push CI **`26035713428`**（記録）。
**内容**: US cache population runbook（**docs-only**）。詳細は **[docs/56_r6_15_c_us_cache_population_runbook.md](./56_r6_15_c_us_cache_population_runbook.md)**。
**ruleset 注記**: required check context を **`tests` → `test`** に API patch 後 merge（2026-05-18）。

### 次タスク（候補）

- **R6.16** / **R6.17**（runbook §7 参照）· **R6.14-J**（**別承認**）。

---

## R6.15-D — Codex light review prompt（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`20bed56`** · PR **#4** squash merge · main push CI **`26035884499`** success。
**詳細**: **[docs/57_r6_15_d_codex_light_review_prompt.md](./57_r6_15_d_codex_light_review_prompt.md)**。

**次候補**: **R6.15-E**（Codex 結果 docs · 任意）· **R6.16**（runbook §7 · **別承認**）。

---

## R6.15-E — Codex light review result（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`b23ebe1`** · PR **#5** squash merge。
**詳細**: **[docs/58_r6_15_e_codex_light_review_result.md](./58_r6_15_e_codex_light_review_result.md)**。

**次候補**: **R6.15-F**（Codex MEDIUM follow-ups）· **R6.16-A**（read-only cache inventory · runbook §7.1）。

---

## R6.15-F — Codex safety gate follow-ups（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`4a16043`** · PR **#6** squash merge。
**内容**: `main_gate.sh` detached HEAD 拒否 · docs/55 required check **`test`** 整合 · runbook §7.1 entry criteria。

---

## R6.16-A — US cache inventory MVP（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`243f37c`** · PR **#7** squash merge。
**内容**: read-only cache inventory CLI + pure helper。詳細 **[docs/59_r6_16_a_us_cache_inventory_mvp.md](./59_r6_16_a_us_cache_inventory_mvp.md)**。

---

## R6.16-B — US cache inventory hardening（完了・`main` 反映済み）

**コミット（`main` 取り込み）**: **`a34562f`** · PR **#8** squash merge。
**内容**: JSON `summary` · Markdown Summary · 安定 `reason` コード。詳細 **[docs/60_r6_16_b_us_cache_inventory_hardening.md](./60_r6_16_b_us_cache_inventory_hardening.md)**。

**real cache smoke（参考）**: total 16 · ok 3（MSFT/GOOGL/GLDM）· missing 13。

---

## R6.16-C — Operator-gated ingest design（完了・`main` 反映済み · docs-only）

**コミット（`main` 取り込み）**: **`45b3796`** · PR **#9** squash merge。
**内容**: missing-only · 二重ゲート · batch 上限 · inventory before/after · rollback。詳細 **[docs/61_r6_16_c_operator_gated_ingest_design.md](./61_r6_16_c_operator_gated_ingest_design.md)**。
**実装着手**: **別承認**（ingest plan CLI は未実装）。

---

## R6.16-D — US cache full population status（完了・`main` 反映済み · docs-only）

**コミット（`main` 取り込み）**: PR **#10** squash merge（**`work/r6-16-d-us-cache-full-population-docs`**）。
**内容**: 手動 / bulk **gated cache ingest** 完了後の **population 運用記録**（watchlist **16 symbols · ok 16 · missing 0** · missing **13 → 0** · invalid / insufficient / stale_unknown **0 維持**）。詳細 **[docs/62_r6_16_d_us_cache_full_population_status.md](./62_r6_16_d_us_cache_full_population_status.md)**。
**境界**: **R6.16-E freshness 拡張とは別物**（population 記録 vs `ok` / `fresh_enough` 分離）。cache JSON と **`.env` は local / gitignore · 未コミット**。**コード変更なし** · **daily / signals default 接続なし** · **ingest plan CLI は別承認** · **R6.17 は別承認**。

---

## R6.16-E — US cache inventory freshness（完了・`main` 反映済み · read-only 拡張）

**コミット（`main` 取り込み）**: **`39304a1`** · PR **#11** squash merge。
**内容**: inventory **`ok`** vs **`fresh_enough`** 分離（`latest_date` · `freshness_status` · summary · 初期 **7 暦日** cutoff）。詳細 **[docs/63_r6_16_e_us_cache_inventory_freshness.md](./63_r6_16_e_us_cache_inventory_freshness.md)**。
**CI**: GitHub Actions **`test`** — pass（PR #11 · main post-merge）。
**境界**: **R6.16-D population 記録とは別物**。**daily / signals default 接続なし** · **ingest plan CLI / R6.17 は別承認**。

**次候補**: **R6.17** daily 接続判断（**別承認**）。

---

## R6.16-F — Agent workflow standardization（完了・`main` 反映済み · docs/templates）

**コミット（`main` 取り込み）**: **`1fa2fb1`** · PR **#12** squash merge。
**内容**: **最小人間貼り付け・最大自走**を標準化（**`.agent/*`** · **`CLAUDE.md`** on **`main`**）。Cursor / Codex / Claude 役割分担 · リスク別手順 · **単一 Markdown 最終報告圧縮** · **sound / notification policy**（`.agent/standard_clauses.md`）。詳細 **[docs/64_r6_16_f_agent_workflow_standardization.md](./64_r6_16_f_agent_workflow_standardization.md)**。
**境界**: **product code / workflow / Makefile / pyproject 変更なし** · **live HTTP / cache write / daily·signals default 変更なし** · **R6.17 前の運用基盤**。

**次候補**: **R6.17** opt-in cache-only preview（**別承認** · 下記 planning PR）。

---

## R6.16-G — Docs status microfix（完了・`main` 反映済み · docs-only）

**コミット（`main` 取り込み）**: **`a625094`** · PR **#13** squash merge。
**内容**: `docs/01` の R6.16-F **main 反映済み**表記 · `docs/62` 先頭の branch-only 表記修正。

---

## R6.17 — Opt-in US cache-only preview（完了 · `main` 反映済み）

**コミット（`main` 取り込み）**: **`879fe47`** · PR **#16** squash merge。
**内容**: `daily --us-cache-preview` · read-only cache 表 · `return_1d` / `volume_status` · freshness note。設計 **[docs/65](./65_r6_17_opt_in_us_cache_preview_plan.md)** · 実装 **[docs/67](./67_r6_17_opt_in_us_cache_preview_implementation.md)** · smoke **[docs/68](./68_r6_17_a_opt_in_us_cache_preview_smoke.md)**。
**境界**: **opt-in only** · **default 変更なし** · **live HTTP / cache write なし** · **運用有効化は operator 判断**。

---

## R6.17-B — Opt-in US cache preview runbook（完了 · `main` 反映済み · docs-only）

**コミット（`main` 取り込み）**: **`8a53013`** · PR **#18** squash merge。
**内容**: operator 向け **`daily --us-cache-preview`** 手順 · stale（MSFT/GOOGL/GLDM）扱い · stale refresh 計画（未実行）。詳細 **[docs/69_r6_17_b_opt_in_us_cache_preview_runbook.md](./69_r6_17_b_opt_in_us_cache_preview_runbook.md)**。

---

## R6.17-C — Operational readiness package（完了 · `main` 反映済み · docs/templates）

**コミット（`main` 取り込み）**: **`ee8dda6`** · PR **#19** squash merge。
**内容**: operational readiness · stale refresh approval · default enablement checklist · agent prompts。詳細 **[docs/70](./70_r6_17_c_operational_readiness.md)** · **[docs/71](./71_r6_17_c_stale_refresh_approval_package.md)** · **[docs/72](./72_r6_17_c_default_enablement_checklist.md)**。
**Codex post-merge**: `APPROVED_WITH_MINOR_NOTES`（docs 表記のみ · blocker なし）。

---

## R6.17-D — Stale refresh MSFT/GOOGL/GLDM（完了 · `main` 反映済み · operator）

**コミット（status docs）**: **`ba38ee9`** · PR **#20** squash merge。
**実施**: 2026-05-20 · 詳細 **[docs/73_r6_17_d_stale_refresh_status.md](./73_r6_17_d_stale_refresh_status.md)**。
**結果**: fresh_enough **13→16** · stale **3→0** · gated live HTTP + cache write（**3 symbols のみ**）。
**境界**: **default 変更なし** · **cache JSON 未コミット** · **default enablement は別承認**。

---

## R6.18-B+C — Cache-only connection planning（完了 · `main` 反映済み · docs/templates）

**コミット（`main` 取り込み）**: **`3e71743`** · PR **#21** squash merge。
**内容**: US cache preview **cache-only 接続設計（B）** · **default enablement readiness（C）** · B1 推奨。 **[docs/74](./74_r6_18_bc_cache_only_connection_design.md)** · **[docs/75](./75_r6_18_bc_default_enablement_readiness_checklist.md)** · **[docs/76](./76_r6_18_bc_implementation_review_pack.md)**。

---

## R6.18-D — Docs whitespace microfix（完了 · `main` 反映済み · docs-only）

**コミット（`main` 取り込み）**: PR **#22** · docs/74–76 行末空白除去。

---

## R6.18-E — B1 signals US cache preview（完了 · `main` 反映済み）

**コミット（`main` 取り込み）**: **`9c6f5e5`** · PR **#23** squash merge。
**内容**: opt-in **`signals --us-cache-preview`** · JSON `us_cache_preview` · Markdown preview 節。詳細 **[docs/77](./77_r6_18_e_b1_signals_us_cache_preview.md)**。
**Codex post-merge**: `APPROVED_WITH_MINOR_NOTES`（blocker なし）。
**境界**: **no live HTTP** · **no cache write** · **default enablement 未承認**。

---

## R6.18-F — Signals preview ops evidence（完了 · `main` 反映済み · docs/templates）

**コミット（`main` 取り込み）**: **`f349c50`** · PR **#24** squash merge。
**内容**: R6.18-E 完了反映 · docs/77 修正 · **[docs/78](./78_r6_18_f_signals_us_cache_preview_operational_evidence.md)** 運用 evidence 枠。

---

## R6.18-G — Signals preview smoke evidence（完了 · `main` 反映済み · docs-only）

**コミット**: PR **#25**（smoke #1 · `cd86396`）· PR **#26**（smoke #2 · `318a7d9`）。
**結果**: read-only smoke **2 件** · いずれも pass（stale 0 · fresh_enough 16）。
**注意**: 両記録とも暦日 **2026-05-20**（#2 は別セッション）。

---

## R7.0-B3S — JP Core50 cache fill continuation（完了 · 部分 ingest · 429 停止 · docs-only）

**結果**: B3R 同ポリシーで **11 銘柄** cache 追加 · Core50 **19→30/50**（目標 ≥40 **未達**）· batch 4 で **429**（6594）により停止。詳細 **[docs/88](./88_r7_0_b3s_jp_core50_cache_fill_continuation.md)**。残り 20 銘柄は **B3S2**（長い待機 or 1 銘柄/バッチ）推奨。

---

## R7.0-B3S2 — JP Core50 cache fill（完了 · 目標達成 · ローカル ingest · docs-only）

**結果**: **1 銘柄/バッチ** · **120s** · gated live + write · Core50 **30→40/50**（目標 ≥40 **達成**）· HTTP 400/429 なし。証跡 **[docs/94](./94_r7_0_b3s2_core50_cache_fill_evidence.md)**。キャッシュ JSON はローカルのみ。続報 **[docs/95](./95_r7_0_b4_jp_discovery_reevaluation.md)**（**案 A: R7.0-C**）。

---

## R7.0-B4 — JP discovery re-evaluation after Core50 40/50（完了 · read-only · docs-only）

**結果**: Core50 **40/50（≥80 bars）** を再確認 · `discover-jp` ranked **20** · insufficient **10**。推奨は **案 A: R7.0-C US MVP**。詳細 **[docs/95](./95_r7_0_b4_jp_discovery_reevaluation.md)** · ローカル証跡は `outputs/`（未コミット）。

---

## R7.0-C — US Universe Scanner MVP（完了 · cache-only discovery · `main` 反映待ち）

**結果**: `discover-us` CLI と US scanner を追加（cache read-only）。`config/us_universe_scanner_mvp.yaml` とテストを整備し、JP と同思想の observation-only 出力契約を固定。詳細 **[docs/96](./96_r7_0_c_us_universe_scanner_mvp.md)**。

---

## R7.0-B3R — JP Core50 cache retry diagnostics（完了 · 部分 ingest 成功 · docs-only）

**結果**: 日付範囲短縮 + バッチ≤3 で **10 銘柄** cache 追加 · Core50 **9→19/50**。詳細 **[docs/87](./87_r7_0_b3r_jp_core50_cache_retry_diagnostics.md)**。残り 31 銘柄は追加 B3R バッチ待ち。

---

## R7.0-B3 — JP Core50 gated cache fill（完了 · ingest 失敗 · docs-only）

**結果**: batch 1/5 試行 · **cache_written 0** · HTTP 400/429 · カバレッジ **9/50** 変化なし。詳細 **[docs/86](./86_r7_0_b3_jp_core50_cache_fill.md)**。再試行はレート制限/プラン確認後。

---

## R7.0-B2 — JP universe/cache expansion（完了 · `main` 反映済み · Core50）

**内容**: `config/jp_universe_core50.yaml`（50 銘柄）· display names 拡張 · cache カバレッジ **9/50** · ingest は **R7.0-B3** へ。詳細 **[docs/85](./85_r7_0_b2_jp_universe_cache_expansion.md)**。

---

## R7.0-B1 — JP discovery scanner evaluation（完了 · docs-only · 評価記録）

**内容**: post-merge `discover-jp` 評価 · cache 11 銘柄 · **次推奨 R7.0-B2**（universe/cache 拡張）。詳細 **[docs/84](./84_r7_0_b1_jp_discovery_scanner_evaluation.md)**。

---

## R7.0-B — JP Universe Scanner MVP（完了 · `main` 反映済み · cache-only discovery）

**コミット（`main` 取り込み）**: **`7891b3b`** · PR **#31** squash merge。
**内容**: `discover-jp` CLI · `discovery/jp_universe_scanner.py` · [docs/83](./83_r7_0_b_jp_universe_scanner_mvp.md)。
**境界**: cache/fixture only · observation-only · **default 変更なし** · R7.0-A planning を実装基準。

---

## R6.19-G — Japanese Gmail narrative + no attachments（完了 · PR #41 · gated send 確認）

**内容**: `.md` 添付廃止 · ナラティブ（注目/銘柄別/次に確認）· HTML 本文 · **14 tests** pass · gated send OK。詳細 **[docs/92](./92_r6_19_g_japanese_gmail_narrative.md)**。

---

## R6.19-E — Japanese daily Gmail report（完了 · 日本語レンダリング · gated send 確認済み）

**結果**: `daily_email.py` 日本語化 · dry-run / **13 tests** pass · gated `--send` pass · ユーザー目視で日本語受信確認。詳細 **[docs/91](./91_r6_19_e_japanese_gmail_report.md)**。credentials/token 未コミット · live HTTP なし。

---

## R6.19-F — Daily Gmail 07:00 launchd setup（完了 · ローカル LaunchAgent · docs-only）

**結果**: `com.invest-alpha-os.daily-gmail-report` を **07:00 ローカル**で bootstrap · dry-run OK · 本日 `email_sent.json` なしのため追加送信は未実施。詳細 **[docs/90](./90_r6_19_f_launchd_0700_gmail_setup.md)**。**R6.19-E** マージ後に 07:00 日本語送信が恒久化。

---

## R6.19-D — Gmail OAuth token bootstrap（完了 · ローカル token 確認済み）

**内容**: 初回 `daily-email --send` で OAuth token 作成/refresh · [docs/89](./89_r6_19_d_gmail_oauth_token_bootstrap.md)。

---

## R6.19-B / R7.0-A — Daily 07:00 Gmail schedule + discovery planning（完了 · `main` 反映済み · ops/docs）

**コミット（`main` 取り込み）**: **`fd4bbaa`** · PR **#29** squash merge。
**内容**: `scripts/run_daily_gmail_report.sh` · launchd 07:00 template · [docs/81](./81_r6_19_b_daily_0700_gmail_delivery_runbook.md) · [docs/82](./82_r7_0_a_discovery_engine_planning.md)。
**境界**: Gmail **gated** · default 変更なし · discovery は planning のみ · live send は OAuth 設定後。

---

## R6.19-A — Gmail delivery and display names（完了 · `main` 反映済み）

**コミット（`main` 取り込み）**: **`aa8c966`** · PR **#28** squash merge。
**内容**: 表示名 · `daily-email` · 詳細 **[docs/80](./80_r6_19_a_gmail_delivery_and_display_names.md)**。

---

## R6.18-H — Default-readiness review package（完了 · `main` 反映済み · docs-only）

**コミット（`main` 取り込み）**: **`07c1235`** · PR **#27** squash merge。
**内容**: default-readiness レビュー · 同一暦日 caveat · **default ブロック継続** · **R6.18-I** 推奨。詳細 **[docs/79](./79_r6_18_h_default_readiness_review_package.md)**。

**次候補**: **R6.18-I** 後日暦日 smoke · **R6.19-A** Gmail/表示名。

---

## R6.17-pre — Pre-implementation review pack（完了 · `main` 反映済み · prompts）

**コミット（`main` 取り込み）**: PR **#15** · **`36615c9`** 系（review prompts on main）。
**内容**: Codex / Claude Code 向け review prompts。詳細 **[docs/66_r6_17_pre_implementation_review_pack.md](./66_r6_17_pre_implementation_review_pack.md)**。

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
