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

### Task 5 — 完了（live smoke 準備・V2 daily bars 正規化）

- **`normalize_v2_daily_bars_response`**：`data` / `daily_quotes` / `bars` / `results` の順で **list** を検査。**空 list は `success` と `row_count=0`**。list 以外は **`invalid_response`**。
- **`get_daily_quotes`（V2 live）** の成功判定を上記に集約。**`row_count` / `source_key` / `date_from` / `date_to`** を返す（行データ・API Key は出さない）。
- **`debug jquants-daily-quotes`**：**`--live` なしは dry-run exit 0**；**一覧キーだけでなく値が配列であること**を確認してから **`success`**。CLI 出力を安全な要約のみに。**実 API は人間のローカル・手順 [09](./09_jquants_local_manual_test.md) のみ**。
- **テスト**：normalize・CLI `--live` exit・標準出力に秘密なし。**CI は live 不使用**。

### Task 6 以降（未着手）

- Watchlist 向けデータ取得での stub / live 切替、その他エンドポイント

---

関連: [07_ai_development_workflow.md](./07_ai_development_workflow.md)
