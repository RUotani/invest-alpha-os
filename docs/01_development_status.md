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
- **`debug jquants-daily-quotes --live`**: 実 HTTP は **`JQUANTS_ALLOW_LIVE_HTTP=true` とセット**の二重ゲート
- **`make verify` / GitHub Actions**: 実接続なし

### Task 3 — 完了（Version2 前提の設定・手動ガイド）

- **[docs/09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)** — ローカル手動接続の手順（AI に秘密を渡さない・二重ゲート・トラブルシュート）
- **`JQUANTS_API_VERSION` / `JQUANTS_API_BASE_URL`**（`.env.example`・`JQuantsClient`）— **BASE URL 未設定時は `not_configured`**、V1 固定デフォルト URL なし
- **`config/market_data.yaml`** — `api_version`、`ci_live_http: disabled`、`manual_live_http: double_gate_required` 等
- **実 API 接続・Version2 正式パス確定は Task 4 以降**

**計画・運用詳細**: [08_phase1a_jquants_plan.md](./08_phase1a_jquants_plan.md) · 手動確認: [09_jquants_local_manual_test.md](./09_jquants_local_manual_test.md)

### Task 4 以降（未着手）

- 公式 Version2 のエンドポイント・レスポンス確定、正規化、トークン自動 refresh、本番的な実接続テスト

---

関連: [07_ai_development_workflow.md](./07_ai_development_workflow.md)
